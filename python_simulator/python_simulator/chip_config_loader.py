"""
Chip configuration loader with mapping support
"""
import json
import os
import logging
from typing import Dict, List, Tuple


class ChipConfigLoader:
    """Load and manage chip configurations with work area support"""
    
    def __init__(self, config_dir: str = None):
        """
        Initialize chip configuration loader
        
        Args:
            config_dir: Directory containing chip config files and mapping
        """
        if config_dir is None:
            # Default to ChipConfig directory relative to this file
            config_dir = os.path.join(os.path.dirname(__file__), "ChipConfig")
        
        self.config_dir = config_dir
        self.logger = logging.getLogger("ChipConfigLoader")
        self.mappings = {}
        self._load_mappings()
    
    def _load_mappings(self):
        """Load chip configuration mappings"""
        mapping_file = os.path.join(self.config_dir, "chip_config_mapping.json")
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.mappings = data.get('mappings', {})
                self.logger.info(f"Loaded {len(self.mappings)} chip mappings from {mapping_file}")
                
                # Log available chips
                for chip_id, chip_info in self.mappings.items():
                    work_areas = list(chip_info.get('work_areas', {}).keys())
                    self.logger.info(f"  - Chip {chip_id}: {len(work_areas)} work areas {work_areas}")
        except FileNotFoundError:
            self.logger.error(f"Mapping file not found: {mapping_file}")
            self.mappings = {}
        except Exception as e:
            self.logger.error(f"Failed to load chip mappings: {e}")
            self.mappings = {}
    
    def get_chip_config(self, chip_id: str) -> Tuple[Dict, List[int]]:
        """
        Get chip configuration for specified chip ID
        
        Args:
            chip_id: Chip ID as string (e.g., "72", "HanYuan_01")
        
        Returns:
            (chip_config_dict, point_label_list)
            - chip_config_dict: Dictionary mapping work area labels to config data
            - point_label_list: List of available work area labels as integers
        """
        if chip_id not in self.mappings:
            self.logger.warning(f"Unknown chip ID: {chip_id}")
            return {}, []
        
        chip_info = self.mappings[chip_id]
        work_areas = chip_info.get('work_areas', {})
        point_label_list = [int(label) for label in work_areas.keys()]
        
        # Load configurations for all work areas
        chip_config = {}
        for label, area_info in work_areas.items():
            config_file = area_info.get('config_file')
            config_path = os.path.join(self.config_dir, config_file)
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    chip_config[label] = config_data
                    self.logger.info(f"Loaded config for chip {chip_id}, area {label} from {config_file}")
            except FileNotFoundError:
                self.logger.error(f"Config file not found: {config_path}")
                chip_config[label] = {}
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON from {config_file}: {e}")
                chip_config[label] = {}
            except Exception as e:
                self.logger.error(f"Failed to load {config_file}: {e}")
                chip_config[label] = {}
        
        return chip_config, point_label_list
    
    def get_available_chips(self) -> List[Dict]:
        """
        Get list of available chips
        
        Returns:
            List of chip information dictionaries
        """
        chips = []
        for chip_id, chip_info in self.mappings.items():
            chips.append({
                'chip_id': chip_info.get('chip_id'),
                'chip_name': chip_info.get('chip_name'),
                'system_type': chip_info.get('system_type'),
                'work_areas': list(chip_info.get('work_areas', {}).keys())
            })
        return chips
    
    def reload_mappings(self):
        """Reload chip configuration mappings"""
        self.logger.info("Reloading chip mappings...")
        self._load_mappings()
    
    def get_chip_info(self, chip_id: str) -> Dict:
        """
        Get chip information without loading full config
        
        Args:
            chip_id: Chip ID as string
        
        Returns:
            Chip information dictionary or empty dict if not found
        """
        return self.mappings.get(chip_id, {})
