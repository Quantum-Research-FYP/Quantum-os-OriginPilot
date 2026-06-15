# Origin PilotOS Installation Package Guide

Welcome to Origin PilotOS, a quantum operating system developed by Origin Quantum. This package includes the automated deployment program, measurement and control simulation service examples, and related technical documentation.

This document is intended to help you quickly understand the directory structure and guide you through system installation, deployment, and integration.

## 📂 Directory Structure

After extracting the package, the following files and directories are included:

| File/Directory Name                       | Description                                                  |
| ----------------------------------------- | ------------------------------------------------------------ |
| **pilotos-4.1.tar.gz**                    | **Automated deployment package**. Contains the core PilotOS system and deployment script (`AutoDeploy.py`). |
| **python_simulator.tar.gz**               | **Heterogeneous quantum chip measurement & control simulation service**. Provides reference examples for integrating custom hardware. |
| **Origin PilotOS User Manual.pdf**        | Complete user manual, including detailed installation steps (Chapter 2) and feature descriptions. |
| **Simulation Service Guide.pdf**          | Instructions on how to run and use the `python_simulator` service. |
| **PilotOS Upgrade Guide.pdf**             | If you have already deployed version 4.0, refer to this guide for upgrade instructions. |
| **Heterogeneous_Quantum_Chip_Interface/** | (Directory) Contains communication protocol documentation for integration between measurement & control services and PilotOS. |
| **English_documents/**                    | English documentation                                        |

------

## 🚀 Quick Start

### 1. System Deployment

Origin PilotOS provides a one-click automated deployment script. Follow these steps:

1. **Extract the package**:
   Extract `pilotos-4.*.tar.gz` to the target server.

   ```bash
   tar -zxvf pilotos-4.*.tar.gz
   cd pilotos-4.*
   ```

2. **Run automated deployment**:
   Execute the deployment script in the extracted directory.

3. **Detailed guidance**:
   For environment dependencies, parameter configuration, and troubleshooting during deployment, refer to **Chapter 2** of *Origin PilotOS User Manual.pdf*.

### 2. Measurement & Control Integration

If you need to integrate your own quantum chip measurement and control system with Origin PilotOS, or perform development and debugging, use the provided simulation service.

- **Run simulation service**:
  Extract `python_simulator.tar.gz` and follow *Simulation Service Guide.pdf* to start the service.
  This service demonstrates standard measurement and control response logic.
- **Protocol-based integration**:
  For integration with real hardware, refer to the documentation under the **Heterogeneous_Quantum_Chip_Interface/** directory.
  These documents define the communication interface specifications between PilotOS and underlying measurement & control hardware.

------

## 📚 Documentation Index

- **Installation & deployment issues** → Refer to *Origin PilotOS User Manual.pdf*
- **Simulator usage** → Refer to *Simulation Service Guide.pdf*
- **Hardware integration development** → Refer to **Heterogeneous_Quantum_Chip_Interface/** directory

------

*Copyright © 2017 - 2026 Origin Quantum. All Rights Reserved.*