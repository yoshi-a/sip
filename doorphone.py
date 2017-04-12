#!/usr/bin/env python

import linphone
import logging
import signal
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)
GPIO.setup(13, GPIO.IN)
GPIO.add_event_detect(13, GPIO.BOTH)

class SecurityCamera:
    def __init__(self, username='', password='', whitelist=[], camera='', snd_capture='', snd_playback=''):
        self.quit = False
        self.whitelist = whitelist
        callbacks = {
            'call_state_changed': self.call_state_changed,
                }

            # Configure the linphone core
        logging.basicConfig(level=logging.DEBUG)
        signal.signal(signal.SIGINT, self.signal_handler)
        self.SipTransports = linphone.SipTransports
        linphone.set_log_handler(self.log_handler)
        self.core = linphone.Core.new(callbacks, None, None)
        self.core.max_calls = 1
        self.core.echo_cancellation_enabled = False
        self.core.video_capture_enabled = True
        self.core.video_display_enabled = False
        #self.core.nat_policy.stun_server = 'stun.linphone.org'
        #self.core.nat_policy.ice_enabled = False
        if len(camera):
            self.core.video_device = self.video_devices['name'] #camera
        if len(snd_capture):
            #self.core.capture_device = self.sound_devices['name']
            print(self.core.sound_device_can_capture(snd_capture))
            print(self.core.sound_device_can_capture(self.sound_devices['name']))
            print(snd_capture)
            print(self.video_devices)
            self.core.capture_device = snd_capture
        if len(snd_playback):
            self.core.playback_device = snd_playback

            # Only enable PCMU and PCMA audio codecs
        for codec in self.core.audio_codecs:
            if codec.mime_type == "PCMA" or codec.mime_type == "PCMU":
                self.core.enable_payload_type(codec, True)
            else:
                self.core.enable_payload_type(codec, False)
            
            # Only enable VP8 video codec
        for codec in self.core.video_codecs:
            if codec.mime_type == "VP8":
                self.core.enable_payload_type(codec, True)
            else:
                self.core.enable_payload_type(codec, False)
                
        self.configure_sip_account(username, password)
    @property
    def video_devices(self):
        try:
            all_devices = []
            for video_device in self.core.video_devices:
                all_devices.append({
                    'name':       video_device
                })
            return all_devices[0]
        except Exception:
            return []

    @property
    def sound_devices(self):
        try:
            all_devices = []
            for sound_device in self.core.sound_devices:
                all_devices.append({
                    'name':       sound_device,
                    'capture':    self.core.sound_device_can_capture(sound_device),
                    'record':     self.core.sound_device_can_playback(sound_device)
                })
            return all_devices[0]
        except Exception as exp:
            logger.exception(exp)
            return []
        
    def signal_handler(self, signal, frame):
        self.core.terminate_all_calls()
        self.quit = True
            
    def log_handler(self, level, msg):
        method = getattr(logging, level)
        method(msg)
        
    def call_state_changed(self, core, call, state, message):
        if state == linphone.CallState.IncomingReceived:
            if call.remote_address.as_string_uri_only() in self.whitelist:
                params = core.create_call_params(call)
                core.accept_call_with_params(call, params)
            else:
                core.decline_call(call, linphone.Reason.Declined)
                chat_room = core.get_chat_room_from_uri(self.whitelist[0])
                msg = chat_room.create_message(call.remote_address_as_string + ' tried to call')
                chat_room.send_chat_message(msg)
                
    def configure_sip_account(self, username, password):                               # Configure the SIP account
        proxy_cfg = self.core.create_proxy_config()
        proxy_cfg.identity_address = self.core.create_address('sip:{username}@192.168.0.11:5060'.format(username=username))
        proxy_cfg.server_addr = 'sip:192.168.0.11:5062'
        proxy_cfg.register_enabled = True
        self.core.add_proxy_config(proxy_cfg)
        auth_info = self.core.create_auth_info(username, None, password, None, None, '192.168.0.11')
        self.core.add_auth_info(auth_info)
        
    def run(self):
        while not self.quit:
            self.core.iterate()
            if GPIO.event_detected(13) and self.core.current_call is None:
                if len(self.core.video_devices)!=0: #todo
                    self.core.invite('sip:5130@192.168.0.13:5060')
            time.sleep(0.3)
            
def main():
    cam = SecurityCamera(username='5134', password='PASSWORD', whitelist=['sip:192.168.0.11:5062'], camera='V4L2: /dev/video0', snd_capture='ALSA: USB Device 0x46d:0x825')
    cam.run()
            
main()
