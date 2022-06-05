import pyaudio
import wave
import struct
import math
from simplejson import load
import analyze
import config as cfg
import os
import sys
import multiprocessing as mp




def get_rms(block):
    SHORT_NORMALIZE = (1.0/32768.0)
    # RMS amplitude is defined as the square root of the 
    # mean over time of the square of the amplitude.
    # so we need to convert this string of bytes into 
    # a string of 16-bit samples...

    # we will get one short out for each 
    # two chars in the string.
    count = len(block)/2
    format = "%dh"%(count)
    shorts = struct.unpack( format, block )

    # iterate over the block.
    sum_squares = 0.0
    for sample in shorts:
    # sample is a signed short in +/- 32768. 
    # normalize it to 1.0
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n

    return math.sqrt( sum_squares / count )

def listener(q: mp.Queue):
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    CHUNK = 1024
    RECORD_SECONDS = 10
    WAVE_OUTPUT_FILENAME = "file.wav"
    
    times = 0
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                rate=RATE, input=True,
                frames_per_buffer=CHUNK)
    print ("recording...")
    frames = []
    
    while True:
        data = stream.read(CHUNK)
        if get_rms(data) > 0.1:
            print("recording")
            times = times + 1
            filename = "file" + str(times) + ".wav"
            frames = []
            for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK)
                frames.append(data)
                print(i)



                # save the audio frames as .wav file

                
            waveFile = wave.open(filename, 'wb')
            waveFile.setnchannels(CHANNELS)
            waveFile.setsampwidth(audio.get_sample_size(FORMAT))
            waveFile.setframerate(RATE)
            waveFile.writeframes(b''.join(frames))
            waveFile.close()
            print("done recording")
            q.put(filename)

def analyzer(q: mp.Queue):


    cfg.MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), cfg.MODEL_PATH)
    cfg.LABELS_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), cfg.LABELS_FILE)
    cfg.TRANSLATED_LABELS_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), cfg.TRANSLATED_LABELS_PATH)
    cfg.MDATA_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), cfg.MDATA_MODEL_PATH)
    cfg.CODES_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), cfg.CODES_FILE)
    cfg.ERROR_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), cfg.ERROR_LOG_FILE)

    cfg.CODES = analyze.loadCodes()
    cfg.LABELS = analyze.loadLabels(cfg.LABELS_FILE)

    cfg.TRANSLATED_LABELS = cfg.LABELS  
    while True:
        filename = q.get()
        cfg.INPUT_PATH = filename
        cfg.OUTPUT_PATH = filename[:len(filename) - 4] + " linnut.txt"
        cfg.FILE_LIST = [cfg.INPUT_PATH]
        if len(cfg.SPECIES_LIST) == 0:
            print('Species list contains {} species'.format(len(cfg.LABELS)))
        else:        
            print('Species list contains {} species'.format(len(cfg.SPECIES_LIST)))
    
        flist = []
        for f in cfg.FILE_LIST:
            flist.append((f, cfg.getConfig()))
        for entry in flist:
            analyze.analyzeFile(entry)

if __name__ == "__main__":


    q = mp.Queue()
    p = mp.Process(target = listener, args=(q,))
    p2 = mp.Process(target = analyzer, args=(q,))

    p.start()
    p2.start()
    p2.join()
    p.join()
