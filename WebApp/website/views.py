from django.shortcuts import render
import librosa
import soundfile
import numpy as np
import pickle
import requests


def home(req):
    pkl_filename = "Emotion_Voice_Detection_Model.pkl"
    # audio = record()

    output = recognise(pkl_filename)
    return render(req, 'index.html', output)


def extract_feature(file_name, mfcc, chroma, mel):
    with soundfile.SoundFile(file_name) as sound_file:
        X = sound_file.read(dtype="float32")
        sample_rate = sound_file.samplerate
        if chroma:
            stft = np.abs(librosa.stft(X))
        result = np.array([])
        if mfcc:
            mfccs = np.mean(librosa.feature.mfcc(y=X, sr=sample_rate, n_mfcc=40).T, axis=0)
        result = np.hstack((result, mfccs))
        if chroma:
            chroma = np.mean(librosa.feature.chroma_stft(S=stft, sr=sample_rate).T, axis=0)
        result = np.hstack((result, chroma))
        if mel:
            mel = np.mean(librosa.feature.melspectrogram(X, sr=sample_rate).T, axis=0)
        result = np.hstack((result, mel))
    return result


def recognise(pkl_filename):
    with open(pkl_filename, 'rb') as file:
        Emotion_Voice_Detection_Model = pickle.load(file)
    audio = [] # need to import
    ans = []
    new_feature = extract_feature(audio, mfcc=True, chroma=True, mel=True)
    ans.append(new_feature)
    ans = np.array(ans)

    return Emotion_Voice_Detection_Model.predict(ans)
