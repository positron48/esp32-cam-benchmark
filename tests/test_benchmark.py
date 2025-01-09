import os
import pytest
from pathlib import Path
import yaml
import json
from run_tests import ESPCamBenchmark

@pytest.fixture
def benchmark():
    """Create benchmark instance for testing"""
    return ESPCamBenchmark()

def test_config_loading(benchmark):
    """Test that configuration is loaded correctly"""
    assert benchmark.config is not None
    assert 'wifi' in benchmark.config
    assert 'camera_resolutions' in benchmark.config
    assert 'video_protocols' in benchmark.config
    assert 'control_protocols' in benchmark.config

def test_results_directories(benchmark):
    """Test that results directories are created"""
    dirs = [
        benchmark.config['results_dir'],
        benchmark.config['video_dir'],
        benchmark.config['logs_dir'],
        benchmark.config['metrics_dir']
    ]
    for dir_path in dirs:
        assert Path(dir_path).exists()
        assert Path(dir_path).is_dir()

def test_protocol_combinations():
    """Test that all protocol combinations are valid"""
    with open('bench_config.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Check video protocols
    assert all(p in ['HTTP', 'RTSP', 'UDP', 'WebRTC', 'none'] 
              for p in config['video_protocols'] + ['none'])
    
    # Check control protocols
    assert all(p in ['HTTP', 'UDP', 'WebSocket', 'none'] 
              for p in config['control_protocols'] + ['none'])

def test_build_parameters():
    """Test that build parameters are correctly formatted"""
    benchmark = ESPCamBenchmark()
    params = {
        'video_protocol': 'HTTP',
        'control_protocol': 'UDP',
        'resolution': 'VGA',
        'quality': 30,
        'metrics': True,
        'raw_mode': False
    }
    
    # Test build command generation
    cmd = benchmark.build_firmware(params)
    assert isinstance(cmd, bool)

def test_results_format(benchmark, tmp_path):
    """Test that results are correctly formatted"""
    # Create a mock results file
    results = {
        'parameters': {
            'video_protocol': 'HTTP',
            'control_protocol': 'UDP',
            'resolution': 'VGA',
            'quality': 30,
            'metrics': True,
            'raw_mode': False
        },
        'timestamp': '20240101_120000',
        'video_metrics': {
            'frames': 100,
            'duration': 10.0,
            'fps': 10.0
        },
        'control_metrics': [
            {
                'command': {
                    'pan': 0,
                    'tilt': 0,
                    'zoom': 0,
                    'led': False,
                    'brightness': 50
                },
                'latency': 0.01,
                'success': True
            }
        ]
    }
    
    # Write results to a temporary file
    results_file = tmp_path / 'results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f)
    
    # Read and validate results
    with open(results_file, 'r') as f:
        loaded_results = json.load(f)
    
    assert loaded_results['parameters'] == results['parameters']
    assert 'timestamp' in loaded_results
    assert 'video_metrics' in loaded_results
    assert 'control_metrics' in loaded_results 