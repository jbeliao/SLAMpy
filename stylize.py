# -*- coding: utf-8 -*-
"""

"""
import pylab as pl
import numpy as np
import TextGrid as tg

def hz2cent(f0_Hz):
    return 1200.0*np.log2( np.maximum(1E-5,np.double(f0_Hz) ))

def relst2register(semitones):
    #from relative semitones to register
    if isinstance(semitones,(int,float)):
        semitones = [semitones]
    result = []
    for st in semitones:
        if   st > 6  : result.append('H')
        elif st > 2  : result.append('h')
        elif st > -2  : result.append('m')        
        elif st > -6  : result.append('l')
        elif st < -6  : result.append('L')
    return result        
        
def averageRegisters(swipeFile,speakerTier=None):
    #if no speaker tier is provided, just take the average of the f0s 
    if speakerTier is None:
        print '     No speaker tier given, just taking mean of f0s as average register';
        pitchs = [x for x in swipeFile if x]
        return np.mean(pitchs)
        
    #get all different speaker names
    speakerNames = set([interval.mark() for interval in speakerTier])
    registers     = {}    
    #for each speaker, compute mean register
    for speaker in speakerNames:
        intervals = [interval for interval in speakerTier if interval.mark()==speaker]        
        #on va calculer la moyenne=sum/n
        sumf0 = 0
        nf0 = 0
        for interval in intervals:
            imin, imax = swipeFile.time_bisect(interval.xmin(),interval.xmax())
            pitchs = [x for x in swipeFile.pitch[imin:imax] if x]
            sumf0 += np.sum(pitchs)
            nf0  += len(pitchs)
        if nf0:
            registers[speaker]=sumf0/np.double(nf0)
        else:
            registers[speaker]=None
    return registers

def SLAM1(semitones):
    #this takes a sequence of semitones and applies the SLAM1 stylization
    display=False
    
    #first, smooth the semitones curves using LOWESS
    if 100<len(semitones):
        r = int(len(semitones)/100.0)   
        semitones = list(np.array(semitones)[::r])
    t = np.array(range(len(semitones)))/float(len(semitones))
    if 10<len(semitones):
        import lowess
        smooth = lowess.lowess(t,semitones)
    else:
        smooth = semitones
    start = smooth[0]
    stop = smooth[-1]
    style = relst2register(start)
    style+= relst2register(stop)
    #identify prominence. Either max or min
    maxdiffpositive = np.max([x-max(start,stop) for x in smooth])
    maxdiffnegative = np.abs(np.min([x-min(start,stop) for x in smooth]))
    if maxdiffpositive  > maxdiffnegative:
        #the max is further from boundaries than the min is
        extremum = maxdiffpositive
        posextremum = np.argmax(smooth)
    else:
        extremum = maxdiffnegative
        posextremum = np.argmin(smooth)
    if extremum>2:
        style+=relst2register(smooth[posextremum])
        if t[posextremum] < 0.3:
            style+='1'
        elif t[posextremum] < 0.7:
            style+='2'
        else:
            style+='3'
    style = ''.join(style)
    if display:
        pl.plot(semitones,'b')
        pl.hold(True)
        pl.plot(smooth,'r')
        pl.title(style)
        pl.show()    
    return (style,smooth)
    
def stylizeObject(target,swipeFile, speakerTier=None,registers=None,stylizeFunction=SLAM1):
    #get stylization for an object that implements the xmin() and xmax()
    #methods.
    if (speakerTier is not None) and (registers is None):
        #if a speaker tier is provided and registers is not already computed,
        #compute it.
        registers = averageRegisters(swipeFile,speakerTier)
    
    #get f0 values
    imin, imax = swipeFile.time_bisect(target.xmin(),target.xmax())
    pitchs = swipeFile.pitch[imin:imax]

    if len(pitchs)<2:
        #skipping interval (unvoiced)
        return ('_',[],[])
        
    #get corresponding interval in the speaker tier
    if speakerTier is not None:
        if isinstance(registers,(int,float)):
            #no speaker tier was provided, registers is only the average f0
            reference = registers
        else:
            #else : getting all speakers of target object
            speakers_intervals = tg.getMatchingIntervals([target],speakerTier,strict=False,just_intersection=True)
            speakers = [i.mark() for i in speakers_intervals]
            speakersCount = dict( (x,speakers.count(x)) for x in set(speakers))
            #counting the speakers
            if len(speakersCount)>1:
                speaker = max(speakersCount,key=speakersCount.get)
                print '     Keeping %s'%speaker, speakersCount
            else:
                #only one speaker for all target intervals
                speaker = speakers[0]
            #reference is the value of the registers for this speaker
            reference = registers[speaker]
    else:
        if not np.isnumeric(registers):
            print 'WARNING : no speaker tier provided and reference is not numeric ! not stylizing.'
            return ''
        reference = registers

    #delta with reference in semitones
    delta_pitchs = [1E-2*(hz2cent(pitch) - hz2cent(reference)) for pitch in pitchs]
    (style,smoothed) = stylizeFunction(delta_pitchs)
    return (style,delta_pitchs,smoothed)
    
