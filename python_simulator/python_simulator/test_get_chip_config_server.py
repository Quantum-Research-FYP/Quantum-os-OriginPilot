#!/usr/bin/env python3
"""
测试服务器的 GetChipConfig 接口
"""
import json
import zmq
import time

def test_get_chip_config():
    """测试获取芯片配置接口"""
    
    # 测试配置
    port = 7000  # 超导系统端口
    timeout = 5000  # 5秒超时
    
    print("=" * 60)
    print("Testing GetChipConfig Server Interface")
    print("=" * 60)
    print(f"Port: {port}")
    print(f"System: Superconducting (ChipID 72)")
    print()
    
    # 创建 ZMQ DEALER socket
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.setsockopt(zmq.RCVTIMEO, timeout)
    socket.setsockopt(zmq.SNDTIMEO, timeout)
    
    try:
        # 连接到服务器
        endpoint = f"tcp://localhost:{port}"
        print(f"Connecting to {endpoint}...")
        socket.connect(endpoint)
        print("✓ Connected\n")
        time.sleep(0.5)  # 等待连接建立
        
        # 测试1: 请求有效的芯片配置 (ChipID: 72)
        print("Test 1: Request valid chip config (ChipID: 72)")
        print("-" * 60)
        
        request = {
            "MsgType": "GetChipConfig",
            "SN": 100,
            "ChipID": 72
        }
        
        print(f"Sending request: {json.dumps(request, indent=2)}\n")
        socket.send_json(request)
        
        try:
            response = socket.recv_json()
            print(f"Response received:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            
            # 验证响应
            if response.get('MsgType') == 'GetChipConfigAck':
                print("\n✓ Test 1 PASSED: Correct message type")
                if response.get('ErrCode') == 0:
                    print("✓ Test 1 PASSED: No error")
                    if 'ChipConfig' in response:
                        chip_config = response['ChipConfig']
                        if isinstance(chip_config, dict) and len(chip_config) > 0:
                            print(f"✓ Test 1 PASSED: Chip config returned with {len(chip_config)} work area(s)")
                            # 检查工作区1的配置
                            if '1' in chip_config:
                                config = chip_config['1']
                                if 'QuantumChipArch' in config:
                                    arch = config['QuantumChipArch']
                                    print(f"✓ Test 1 PASSED: QuantumChipArch found")
                                    print(f"  - Chip: {arch.get('Chip', 'N/A')}")
                                    print(f"  - Qubit Count: {arch.get('QubitCount', 'N/A')}")
                        else:
                            print("✗ Test 1 FAILED: Chip config is empty or invalid")
                    else:
                        print("✗ Test 1 FAILED: ChipConfig field missing")
                else:
                    print(f"✗ Test 1 FAILED: Error code {response.get('ErrCode')}: {response.get('ErrInfo')}")
            else:
                print(f"✗ Test 1 FAILED: Wrong message type: {response.get('MsgType')}")
        except zmq.Again:
            print("✗ Test 1 FAILED: No response received (timeout)")
        
        print("\n")
        
        # 测试2: 请求无效的芯片ID
        print("Test 2: Request invalid chip config (ChipID: INVALID_999)")
        print("-" * 60)
        
        request2 = {
            "MsgType": "GetChipConfig",
            "SN": 101,
            "ChipID": "INVALID_999"
        }
        
        print(f"Sending request: {json.dumps(request2, indent=2)}\n")
        socket.send_json(request2)
        
        try:
            response2 = socket.recv_json()
            print(f"Response received:")
            print(json.dumps(response2, indent=2, ensure_ascii=False))
            
            # 验证错误处理
            if response2.get('MsgType') == 'GetChipConfigAck':
                print("\n✓ Test 2 PASSED: Correct message type")
                if response2.get('ErrCode') != 0:
                    print(f"✓ Test 2 PASSED: Error returned as expected (ErrCode: {response2.get('ErrCode')})")
                    print(f"  Error Info: {response2.get('ErrInfo')}")
                else:
                    print("✗ Test 2 FAILED: Expected error but got success")
            else:
                print(f"✗ Test 2 FAILED: Wrong message type: {response2.get('MsgType')}")
        except zmq.Again:
            print("✗ Test 2 FAILED: No response received (timeout)")
        
        print("\n")
        
        # 测试3: 使用字符串类型的ChipID
        print("Test 3: Request with string ChipID ('72')")
        print("-" * 60)
        
        request3 = {
            "MsgType": "GetChipConfig",
            "SN": 102,
            "ChipID": "72"
        }
        
        print(f"Sending request: {json.dumps(request3, indent=2)}\n")
        socket.send_json(request3)
        
        try:
            response3 = socket.recv_json()
            print(f"Response received:")
            print(json.dumps(response3, indent=2, ensure_ascii=False))
            
            # 验证响应
            if response3.get('MsgType') == 'GetChipConfigAck':
                print("\n✓ Test 3 PASSED: Correct message type")
                if response3.get('ErrCode') == 0:
                    print("✓ Test 3 PASSED: String ChipID works correctly")
                else:
                    print(f"✗ Test 3 FAILED: Error code {response3.get('ErrCode')}: {response3.get('ErrInfo')}")
            else:
                print(f"✗ Test 3 FAILED: Wrong message type: {response3.get('MsgType')}")
        except zmq.Again:
            print("✗ Test 3 FAILED: No response received (timeout)")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        socket.close()
        context.term()
        print("\n" + "=" * 60)
        print("Test Complete!")
        print("=" * 60)

if __name__ == "__main__":
    test_get_chip_config()
