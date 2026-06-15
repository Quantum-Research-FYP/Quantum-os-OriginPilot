"""
Photonic quantum system protocol adapter (光量子通信协议)
"""
import json
import time
from typing import Dict, Any
from config import TaskStatus, ErrorCode


class PhotonicAdapter:
    """Adapter for photonic quantum system protocol"""
    
    @staticmethod
    def parse_general_message(msg: str) -> Dict[str, Any]:
        """Parse general message (flat structure for all message types)"""
        data = json.loads(msg)
        
        result = {
            'msg_type': data.get('MsgType'),
            'sn': data.get('SN'),  # Extract SN directly
        }
        
        # Expand all fields from data so handlers can access them directly
        result.update(data)
        
        return result
    
    @staticmethod
    def parse_task_message(msg: str) -> Dict[str, Any]:
        """Parse task message and extract parameters"""
        data = json.loads(msg)
        
        return {
            'msg_type': data.get('MsgType'),
            'sn': data.get('SN'),
            'task_id': data.get('TaskId'),
            'convert_qprog': data.get('ConvertQProg'),
            'configure': data.get('Configure', {}),
        }
    
    @staticmethod
    def build_task_ack(sn: int, err_code: int = 0, err_info: str = "") -> str:
        """Build task acknowledgment message"""
        return json.dumps({
            'MsgType': 'MsgTaskAck',
            'SN': sn,
            'ErrCode': err_code,
            'ErrInfo': err_info
        })
    
    @staticmethod
    def build_task_status_ack(sn: int, task_id: str, status: TaskStatus) -> str:
        """Build task status acknowledgment message"""
        return json.dumps({
            'MsgType': 'TaskStatusAck',
            'SN': sn,
            'TaskId': task_id,
            'TaskStatus': status.value
        })
    
    @staticmethod
    def build_heartbeat_ack(sn: int, backend: int, topic: str) -> str:
        """Build heartbeat acknowledgment message"""
        return json.dumps({
            'MsgType': 'MsgHeartbeatAck',
            'SN': sn,
            'backend': backend,
            'TimeStamp': int(time.time() * 1000),
            'Topic': topic
        })
    
    @staticmethod
    def build_task_result(sn: int, task_id: str, keys: list, 
                      prob_counts: list, note_time: Dict[str, int], 
                      err_code: int = 0, err_info: str = "") -> str:
        """Build task result message"""
        return json.dumps({
            'MsgType': 'MsgTaskResult',
            'SN': sn,
            'TaskId': task_id,
            'Key': keys,
            'ProbCount': prob_counts,
            'NoteTime': note_time,
            'ErrCode': err_code,
            'ErrInfo': err_info
        })
    
    @staticmethod
    def build_task_result_ack(sn: int, err_code: int = 0, err_info: str = "") -> str:
        """Build task result acknowledgment message"""
        return json.dumps({
            'MsgType': 'MsgTaskResultAck',
            'SN': sn,
            'ErrCode': err_code,
            'ErrInfo': err_info
        })
    
    @staticmethod
    def build_undefined_msg(sn: int, err_code: int, err_info: str) -> str:
        """Build undefined message error response
        
        Used when message type cannot be determined (e.g., JSON parse errors)
        or for general server errors before message type is known.
        
        Args:
            sn: Sequence number (0 if unknown)
            err_code: Error code
            err_info: Error information
            
        Returns:
            Undefined message response string
        """
        return json.dumps({
            'MsgType': 'UndefinedMsg',
            'SN': sn,
            'ErrCode': err_code,
            'ErrInfo': err_info
        })
    
    @staticmethod
    def build_get_chip_config_ack(sn: int, backend: int, point_label_list: list, 
                               chip_config: Dict, err_code: int = 0, 
                               err_info: str = "") -> str:
        """Build get chip config acknowledgment message"""
        return json.dumps({
            'MsgType': 'GetChipConfigAck',
            'SN': sn,
            'backend': backend,
            'PointLabelList': point_label_list,
            'ChipConfig': chip_config,
            'ErrCode': err_code,
            'ErrInfo': err_info
        })
    
    @staticmethod
    def build_get_update_time_ack(sn: int, backend: int, qubits: list, 
                               timestamps: list) -> str:
        """Build get update time acknowledgment message"""
        return json.dumps({
            'MsgType': 'GetUpdateTimeAck',
            'SN': sn,
            'backend': backend,
            'LastUpdateTime': {
                'qubit': qubits,
                'timeStamp': timestamps
            },
            'ErrCode': 0,
            'ErrInfo': ''
        })
    
    @staticmethod
    def build_get_rb_data_ack(sn: int, backend: int, single_gate_depth: list,
                          double_gate_depth: list, single_fidelity: Dict, 
                          double_fidelity: Dict) -> str:
        """Build get RB data acknowledgment message"""
        return json.dumps({
            'MsgType': 'GetRBDataAck',
            'SN': sn,
            'backend': backend,
            'SingleGateCircuitDepth': single_gate_depth,
            'DoubleGateCircuitDepth': double_gate_depth,
            'SingleGateFidelity': single_fidelity,
            'DoubleGateFidelity': double_fidelity,
            'ErrCode': 0,
            'ErrInfo': ''
        })
    
    @staticmethod
    def build_set_vip_ack(sn: int, err_code: int = 0, err_info: str = "") -> str:
        """Build set VIP acknowledgment message"""
        return json.dumps({
            'MsgType': 'SetVipAck',
            'SN': sn,
            'ErrCode': err_code,
            'ErrInfo': err_info
        })
    
    @staticmethod
    def build_release_vip_ack(sn: int, err_code: int = 0, err_info: str = "") -> str:
        """Build release VIP acknowledgment message"""
        return json.dumps({
            'MsgType': 'ReleaseVipAck',
            'SN': sn,
            'ErrCode': err_code,
            'ErrInfo': err_info
        })
    
    @staticmethod
    def build_get_task_result(sn: int, task_id: str, keys: list, 
                          prob_counts: list, note_time: Dict[str, int]) -> str:
        """Build get task result message"""
        return json.dumps({
            'MsgType': 'MsgTaskResult',
            'SN': sn,
            'TaskId': task_id,
            'Key': keys,
            'ProbCount': prob_counts,
            'NoteTime': note_time,
            'ErrCode': 0,
            'ErrInfo': ''
        })
