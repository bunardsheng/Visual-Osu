from pydub import*
import simpleaudio as sa
from numpy import median, diff
import numpy as np
import copy

from libavwrapper import AVConv
from aubio import source, tempo

import sys, os

import time

import math

from pydub import AudioSegment

from pydub.silence import detect_silence

from cmu_112_graphics import *
import random


def appStarted(app):
    app.timerDelay = 10
    app.index = 0
    app.ringList = []
    app.playSong = False
    app.time0 = time.time()
    app.beatsPerSegment = 2
    
    app.segmentLengths = 0

    app.lives = 100
    app.gameOver = False
    app.score = 0
    app.combo = 0
    app.ringTime = 20
    app.ringDecay = 1
    app.ringBeatsAlive = 2
    app.bpm = 120

    app.yaySound = getSound(os.path.join(sys.path[0], "yay click.wav"))
    app.okSound = getSound(os.path.join(sys.path[0], "ok click.wav"))
    app.booSound = getSound(os.path.join(sys.path[0], "no click.wav"))
    app.loseSound = getSound(os.path.join(sys.path[0], "lose.wav"))

################################################################################################################


def get_file_bpm(path, params = None):

    if params is None:
        params = {}
    try:
        win_s = params['win_s']
        samplerate = params['samplerate']
        hop_s = params['hop_s']
    except KeyError:

        samplerate, win_s, hop_s = 96000, 512, 256

    s = source(path, samplerate, hop_s)
    samplerate = s.samplerate
    o = tempo("specdiff", win_s, hop_s, samplerate)
    # List of beats, in samples
    beats = []
    # Total number of frames read
    total_frames = 0
    while True:
        samples, read = s()
        is_beat = o(samples)
        if is_beat:
            this_beat = o.get_last_s()
            beats.append(this_beat)
            #if o.get_confidence() > .2 and len(beats) > 2.:
            #    break
        total_frames += read
        if read < hop_s:
            break

    # Convert to periods and to bpm 
    if len(beats) > 1:
        if len(beats) < 4:
            print("few beats found in {:s}".format(path))
        bpms = 60./diff(beats)
        print(bpms)
        b = median(bpms)
    else:
        b = 0
        print("not enough beats found in {:s}".format(path))
    print(beats)
    return b

################################################################################################################
def getSound(AudioFile):
    return AudioSegment.from_file(AudioFile) # imports using pydub
def makeSound5SecondsLong(sound):
    return sound[:5000]
def lengthSound(sound):
    return sound.duration_seconds

def playSound(sound):
    rawAudioData = sound.raw_data #get raw data from file
    np_array = np.frombuffer(rawAudioData, dtype=np.int16) #converts dumpy to sim
    wave_obj = sa.WaveObject(np_array, 2, 2, 48000)
    return wave_obj.play()

def createSongSplice(sound, segmentLengths):
    print(segmentLengths)
    buffer = 0.1
    songSpliced = []
    cutLength = int((math.floor(lengthSound(sound)/segmentLengths)) * segmentLengths)

    segment = 0
    while segment < cutLength:
        songSpliced.append(sound[segment * 1000: (segment + segmentLengths + buffer) * 1000])
        segment += segmentLengths
    songSpliced.append(sound[1000 * segment: lengthSound(sound)])
    return songSpliced

def createAmplitudeList(splicedSound, segmentLengths, silence_threshold = -50.0):
    amplitudeList = []
    for segment in splicedSound:
        amplitudeList.append(segment.dBFS)
        
    minAmp = min(amplitudeList)
    if minAmp < silence_threshold:
        minAmp = -50.0
    maxAmp = max(amplitudeList)

    return amplitudeList

def getAmplitudeRangeList(splicedSound, amplitudeList, numOfRanges=4):
    rangeLength = math.floor(len(amplitudeList)/numOfRanges)
    borders = []

    border = 0
    print(rangeLength, len(amplitudeList))
    amplitudeListSorted = copy.copy(amplitudeList)
    amplitudeListSorted.sort()
    print(amplitudeListSorted)
    while border < len(amplitudeList):
        print(border)
        borders.append(amplitudeListSorted[border])
        border += rangeLength
    print('BORDERS:',borders)
    amplitudeRangeList = []
    for segment in range(len(splicedSound)):
        for border in range(len(borders)):
            if amplitudeList[segment] >= borders[border]:
                amplitudeRangeList.append(border)
    
    print('AMPRANGELIST:', amplitudeRangeList)
    return amplitudeRangeList

def trimBegAndEndSilence(sound, silence_threshold=-50.0, chunk_size=10):
    begtrim_ms = 0 # ms
    endtrim_ms = len(sound)

    assert chunk_size > 0 # to avoid infinite loop
    while sound[begtrim_ms:begtrim_ms+chunk_size].dBFS < silence_threshold and begtrim_ms < len(sound):
        begtrim_ms += chunk_size

    '''while sound[endtrim_ms:len(sound)].dBFS < silence_threshold - 20 and endtrim_ms > 0:
        endtrim_ms -= chunk_size'''
    
    return sound[begtrim_ms:endtrim_ms]

################################################################################################################
def initializeSong(app):
    sound = getSound((os.path.join(sys.path[0], "Meme Song.wav")))
    sound = trimBegAndEndSilence(sound)

    app.bpm = 120 #get_file_bpm(os.path.join(sys.path[0], "Meme Song.wav")) #190

    segmentLengths = (60/app.bpm) * app.beatsPerSegment

    songSpliced = createSongSplice(sound, segmentLengths)
    app.songSpliced = songSpliced
    amplitudeList = createAmplitudeList(songSpliced, segmentLengths)
    amplitudeRangeList = getAmplitudeRangeList(songSpliced, amplitudeList)

    print(segmentLengths)
    app.segmentLengths = segmentLengths
    app.ringTime = segmentLengths * 40 * app.ringBeatsAlive

    playSong(app, songSpliced, amplitudeList, amplitudeRangeList, segmentLengths)
    


def playSong(app, songSpliced, amplitudeList, amplitudeRangeList, segmentLengths):
    if app.playSong == False:
        app.playSong = True
        
    app.songSpliced = songSpliced
    app.time0 = time.time()

    app.time0 = time.time()


################################################################################################################
def keyPressed(app, event):
    if event.key == 'Enter':
        addRing(app)
        print('initializing')
        appStarted(app)

        initializeSong(app)


def timerFired(app):
    checkGameOver(app)
    if app.gameOver == False:
        ringDecay(app)
        if app.playSong:
            if app.index < len(app.songSpliced):
                bufferRatio = 1
                segmentLengths = (60/app.bpm) * app.beatsPerSegment
                if time.time() - app.time0 >= bufferRatio * segmentLengths:
                    addRing(app)
                    app.index += 1
                    if app.index >= 1:
                        play_obj = playSound(app.songSpliced[app.index - 1])
                    app.time0 = time.time()

def mousePressed(app, event):
    mouseX = event.x
    mouseY = event.y

    index = 0
    while index < len(app.ringList):
        x,y,r1,r2,t = app.ringList[index]
        if ((mouseX - x) ** 2 + (mouseY - y) ** 2) ** 0.5 <= r1:
            #YAY RING TOUCHED
            rhythmAccuracy(app, app.ringList[index])
            app.ringList.pop(index)
            app.combo += 1
            app.score += math.ceil(1.2 ** app.combo) * 10
        else:
            index += 1

def checkGameOver(app):
    if app.lives<= 0 and app.gameOver == False:
        app.gameOver = True
        app.ringList = []
        play_obj = playSound(app.loseSound)


def ringDecay(app):
    index = 0
    while index < (len(app.ringList)):
        x,y,r1,r2,t = app.ringList[index]
        if t <= 0:
            play_obj = playSound(app.booSound)
            app.ringList.pop(index)
            #PLAYER FAILED TO REMOVE CIRCLE -> sdfnsdfsd
            app.combo = 0
            app.lives-= 20
        else:
            app.ringList[index] = (x,y,r1-app.ringDecay,r2,t-1)
            index += 1


def addRing(app):
    minRad = int(app.ringTime * app.ringDecay * 1.2)
    ringTime = app.ringTime
    radius1 = random.randint(minRad, min(app.width, app.height)//4)
    x = random.randint(radius1, app.width - radius1)
    y = random.randint(radius1, app.height - radius1)
    while hasOverlap(app, (x,y,radius1)):

        
        radius1 = random.randint(minRad, min(app.width, app.height)//4)
        x = random.randint(radius1, app.width - radius1)
        y = random.randint(radius1, app.height - radius1)
    
    radius2 = radius1 - app.ringTime * app.ringDecay *(app.ringBeatsAlive - 1)/(app.ringBeatsAlive)
    app.ringList.append((x,y,radius1,radius2,ringTime))

def rhythmAccuracy(app, ring):
    x,y,r1,r2,t = ring
    accuracy = 1 - abs(1-r1/r2)
    print(accuracy)
    if accuracy >= 0.93:
        play_obj = playSound(app.yaySound)
    else:
        play_obj = playSound(app.okSound)

def hasOverlap(app, newRing):
    newX, newY, newR = newRing
    for oldX, oldY, oldR1, oldR2, oldT in app.ringList:
        if ((oldX - newX) ** 2 + (oldY - newY) ** 2)**0.5 < newR + oldR1:
            return True
    return False

def drawRing(app, canvas):
    for (x,y,r1,r2,t) in app.ringList:
        canvas.create_oval(x-r2, y-r2, x+r2, y+r2, fill = None, width = 8, outline = 'black')
        canvas.create_oval(x-r1, y-r1, x+r1, y+r1, fill = None, width = 8, outline = 'gold')
        

def drawNums(app, canvas):
    canvas.create_text(50,50,text = app.life)
    canvas.create_text(app.width - 50,50,text = app.score)
    canvas.create_text(app.width - 50,100,text = app.combo)

def createBar(app, canvas):
    shift = 150
    center = app.width // 2
    right = app.width // 1.15
    
    x0 = right 
    x1 = x0 + (app.width - x0) // 2
    y0 = app.height // 2 - shift
    y1 = app.height // 2 + shift

    #y1 - y0 = whole bar
    #app.lives // 100 * y1-y0
    increasePt = 10
    decreasePt = 10
    ratioBar = (app.lives / 100) * (y1-y0)
    print(app.lives)
    print(ratioBar)
    
    canvas.create_rectangle(x0, y0, x1, y1, width = 8)
    canvas.create_rectangle(x0+8, y1-ratioBar+8, 
    x1-8, y1-8, fill = 'red')
    
def comboBar(app, canvas):
    margin = 20
    center = app.width // 2
    shift = 150
    x0 = center - 0.75*shift
    y0 = app.height // 8 - margin
    x1 = center + 0.75*shift
    y1 = app.height // 8 + margin

    ratioBar = ((app.combo / 100) * (x1-x0))

   

    
    
    canvas.create_rectangle(x0+6, y0+6, 
    x0 + 6 + ratioBar, y1-6, fill = 'green')

    canvas.create_text(app.width//2, app.height//8, text = f'COMBO: {app.combo}',
    font = 'Arial 20 bold')
    canvas.create_rectangle(x0, y0, x1, y1, width = 6)

def youLose(app, canvas):
    center = app.width //2
    vert = app.height // 3
    shift = 50
    
    canvas.create_text(app.width//2, app.height//3, 
    text='you lost haha',font = 'Arial 30 bold')
    canvas.create_oval(center+20-shift, vert+20+shift, center-20-shift, 
    vert-20+shift, fill = 'pink')
    canvas.create_oval(center+20+shift, vert+20+shift, center-20+shift, 
    vert-20+shift, fill = 'pink')
    canvas.create_text(app.width // 1.25, app.height // 1.25, text = 'so bad')
    
    canvas.create_arc(center+shift, vert+3*shift, center-shift, vert+shift, 
    style = CHORD, start = 180, extent = 180, width = 2, fill = 'pink')

def drawScore(app, canvas):
    canvas.create_text(40, 40, anchor = 'nw', text = app.score, font = 'Arial 30 bold')

def redrawAll(app, canvas):
    drawRing(app, canvas)
    createBar(app, canvas)
    comboBar(app, canvas)
    drawScore(app, canvas)
    if app.gameOver:
        youLose(app, canvas)
    
    

runApp(width=1980, height=1080)




'''


print(bpm)
interval = 60/bpm

play_obj = playSound(sound)

time0 = time.time()

while True:
    if time.time() - time0 >= interval:
        play_obj = playSound(bork)
        time0 = time.time()





print('oh no')
play_obj.stop()'''

