#!/usr/bin/env python3

import yaml
import subprocess
import time
import os
import json
import cv2
import numpy as np
import requests
from datetime import datetime
from pathlib import Path

class ESPCamBenchmark:
    def __init__(self, config_file='bench_config.yml'):
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Create results directories
        for dir_path in [self.config['results_dir'], 
                        self.config['video_dir'], 
                        self.config['logs_dir'], 
                        self.config['metrics_dir']]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def build_firmware(self, params):
        """Build firmware with specified parameters"""
        cmd = [
            './build_firmware.sh',
            f'--video={params["video_protocol"]}',
            f'--control={params["control_protocol"]}',
            f'--resolution={params["resolution"]}',
            f'--quality={params["quality"]}',
            f'--metrics={1 if params["metrics"] else 0}',
            f'--raw={1 if params.get("raw_mode", False) else 0}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Build failed: {result.stderr}")
        return True

    def flash_firmware(self, port='/dev/ttyUSB0'):
        """Flash firmware to ESP32-CAM"""
        cmd = ['./flash_firmware.sh', f'--port={port}']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Flash failed: {result.stderr}")
        
        # Wait for device to boot
        time.sleep(5)
        return True

    def capture_video(self, duration, output_path):
        """Capture video stream for specified duration"""
        cap = cv2.VideoCapture('http://esp32-cam.local:80/video')
        
        if not cap.isOpened():
            raise Exception("Failed to open video stream")

        # Get video properties
        fps = 30
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        start_time = time.time()
        frames = 0
        
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
                frames += 1
            else:
                break
        
        actual_duration = time.time() - start_time
        actual_fps = frames / actual_duration
        
        cap.release()
        out.release()
        
        return {
            'frames': frames,
            'duration': actual_duration,
            'fps': actual_fps
        }

    def test_control(self, duration):
        """Test control commands"""
        results = []
        start_time = time.time()
        
        while (time.time() - start_time) < duration:
            # Send test commands
            command = {
                'pan': np.random.randint(-100, 101),
                'tilt': np.random.randint(-100, 101),
                'zoom': np.random.randint(-100, 101),
                'led': bool(np.random.randint(0, 2)),
                'brightness': np.random.randint(0, 101)
            }
            
            send_time = time.time()
            response = requests.post('http://esp32-cam.local:80/control', 
                                  json=command)
            latency = time.time() - send_time
            
            results.append({
                'command': command,
                'latency': latency,
                'success': response.status_code == 200
            })
            
            time.sleep(0.1)  # Don't flood with commands
        
        return results

    def run_test_combination(self, test_params):
        """Run a single test combination"""
        print(f"Running test with params: {test_params}")
        
        # Build and flash firmware
        self.build_firmware(test_params)
        self.flash_firmware()
        
        # Create test results directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        test_dir = Path(self.config['results_dir']) / timestamp
        test_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'parameters': test_params,
            'timestamp': timestamp,
            'video_metrics': None,
            'control_metrics': None
        }
        
        # Warmup period
        time.sleep(self.config['warmup_time'])
        
        # Video test
        if test_params['video_protocol'] != 'none':
            video_path = test_dir / 'capture.mp4'
            results['video_metrics'] = self.capture_video(
                self.config['test_duration'], 
                str(video_path)
            )
        
        # Control test
        if test_params['control_protocol'] != 'none':
            results['control_metrics'] = self.test_control(
                self.config['test_duration']
            )
        
        # Save results
        with open(test_dir / 'results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        return results

    def run_all_tests(self):
        """Run all test combinations"""
        all_results = []
        
        for test_group in self.config['test_combinations']:
            print(f"\nRunning test group: {test_group['name']}")
            
            for test in test_group['tests']:
                # Expand test parameters
                video_protocols = (self.config['video_protocols'] 
                                 if test['video_protocol'] == 'all' 
                                 else [test['video_protocol']])
                
                control_protocols = (self.config['control_protocols'] 
                                   if test['control_protocol'] == 'all' 
                                   else [test['control_protocol']])
                
                resolutions = (self.config['camera_resolutions'] 
                             if test['resolutions'] == 'all' 
                             else test['resolutions'])
                
                qualities = (self.config['jpeg_qualities'] 
                           if test.get('qualities') == 'all' 
                           else test.get('qualities', [10]))
                
                # Run each combination
                for video_proto in video_protocols:
                    for ctrl_proto in control_protocols:
                        for res in resolutions:
                            for quality in qualities:
                                for metrics in test.get('metrics', [True]):
                                    for raw in test.get('raw_mode', [False]):
                                        params = {
                                            'video_protocol': video_proto,
                                            'control_protocol': ctrl_proto,
                                            'resolution': res,
                                            'quality': quality,
                                            'metrics': metrics,
                                            'raw_mode': raw
                                        }
                                        
                                        try:
                                            results = self.run_test_combination(params)
                                            all_results.append(results)
                                        except Exception as e:
                                            print(f"Test failed: {e}")
                                            continue
        
        return all_results

if __name__ == '__main__':
    benchmark = ESPCamBenchmark()
    results = benchmark.run_all_tests()
    
    # Save overall results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'results/summary_{timestamp}.json', 'w') as f:
        json.dump(results, f, indent=2) 