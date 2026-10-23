"""Windows output peak meter. Reads levels only; does not capture audio."""
import time

class AudioMonitor:
    def __init__(self):
        self.meter=None;self.refresh_at=0;self.above=0;self.last_loud=0;self.active=False;self.available=False
    def peak(self):
        now=time.monotonic()
        if now>=self.refresh_at:
            self.refresh_at=now+10
            try:
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
                device=AudioUtilities.GetSpeakers()
                interface=device._dev.Activate(IAudioMeterInformation._iid_,CLSCTX_ALL,None)
                self.meter=interface.QueryInterface(IAudioMeterInformation);self.available=True
            except Exception:
                self.meter=None;self.available=False
        try:return float(self.meter.GetPeakValue()) if self.meter else 0
        except Exception:self.refresh_at=0;return 0
    def poll(self):
        now=time.monotonic()
        if self.peak()>.003:
            self.above+=1;self.last_loud=now
            if self.above>=3:self.active=True
        else:
            self.above=0
            if now-self.last_loud>3:self.active=False
        return self.active
