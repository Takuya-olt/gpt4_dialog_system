import os
import speech_recognition as sr
from speech_recognition import WaitTimeoutError
from datetime import datetime
from pygame import mixer
import time
import shutil
import json
import requests

## 自作モジュール
import alsa_error # alsaの出力をブロック
import mygpt      # GPTの処理

HOSTNAME='voicevox' # for docker
LOGGER_PATH = "./log/asr.txt" # logファイルの出力先
OUTDIR = "./out" # 音声ファイルの出力フォルダ
SPEAKER     = 3 # voiceboxの音声id
FINISH_PHRASE = "終わり"


## マイクで受け取った音声を認識してファイル出力するクラス
class SpeechRecognizer:
    def __init__(self):
        os.makedirs(OUTDIR, exist_ok=True)
        os.makedirs("./log", exist_ok=True)

        with alsa_error.noalsaerr():
            self.rec = sr.Recognizer()
            self.mic = sr.Microphone()

        with alsa_error.noalsaerr(), self.mic as source:
            self.rec.adjust_for_ambient_noise(source)
        
        ## 雑音を無音とみなすための設定
        self.rec.energy_threshold = 280
        self.rec.dynamic_energy_threshold = False

        ## ログ用
        self.speech = []
        return
    
    def __del__(self):
        ## 音声ファイル削除
        shutil.rmtree(OUTDIR)

    ## 音声入力
    ## 戻り値: speech_recognition.AudioData (音声認識エンジンで受け取った音声データ)
    def grab_audio(self) -> sr.AudioData:
        print("何か話してください...")
        try:
            with alsa_error.noalsaerr(), self.mic as source:
                audio = self.rec.listen(source, timeout=5.0)
        except WaitTimeoutError:
            print("[system] タイムアウトしました。")
            raise WaitTimeoutError

        return audio
    
    ## 音声を文字に起こす
    def recognize_audio(self, audio: sr.AudioData) -> str:
        print ("認識中...")
        try:
            ## 文字起こし
            speech = self.rec.recognize_google(audio, language='ja-JP')
        except sr.UnknownValueError:
            print("[system] 認識できませんでした")
            raise sr.UnknownValueError
        except sr.RequestError as e:
            print(f"[system] 音声認識のリクエストが失敗しました:{e}")
            raise sr.RequestError
        return speech

    ## wavファイル生成
    def generate_wav(self, voicepath, text):
        ## audio_query (音声合成用のクエリを作成するAPI)
        res1 = requests.post('http://' + HOSTNAME + ':50021/audio_query',
                            params={'text': text, 'speaker': SPEAKER})
        ## synthesis (音声合成するAPI)
        res2 = requests.post('http://' + HOSTNAME + ':50021/synthesis',
                            params={'speaker': SPEAKER},
                            data=json.dumps(res1.json()))
        ## wavファイルに書き込み
        with open(voicepath, mode='wb') as f:
            f.write(res2.content)

    ## wavファイル再生
    def play_wav(self, voicepath):
        mixer.init()
        mixer.music.load(voicepath)
        mixer.music.play()

        ## 再生が終わるまで待つ
        while mixer.music.get_busy():
            pass
        time.sleep(1)

    ## マイクで受け取った音声を認識してテキストファイルに出力
    def run(self):
        while True:
            ## 音声入力
            try:
                audio = self.grab_audio()
            except WaitTimeoutError:
                continue
            
            ## 文字起こし
            try:
                speech = self.recognize_audio(audio)
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                continue

            
            ## FINISH_PHRASE が認識されたら終了する
            if speech == FINISH_PHRASE:
                print("対話を終了します。")
                break
            else:
                ## ユーザーが話した内容を保存
                self.speech.append("[user] " + speech)
                print(speech)

                voicepath = OUTDIR + "/" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".wav"

                # 文字列が空の場合は処理しない
                if speech == '': continue # <-必要??

                ## GPTで処理
                print("処理中...")
                res = mygpt.ask(speech)
                print(res)

                ## システムの応答を保存
                self.speech.append("[system] " + res)

                ## wavファイル生成
                self.generate_wav(voicepath, res)

                ## wavファイル再生
                self.play_wav(voicepath)
        
        ## log出力
        with open(LOGGER_PATH, mode='a', encoding="utf-8") as out:
            out.write(datetime.now().strftime('%Y%m%d_%H:%M:%S') + "\n\n")
            out.write("\n".join(self.speech) + "\n")
            out.write("==========\n")

if __name__ == "__main__":
    sp = SpeechRecognizer()
    sp.run()