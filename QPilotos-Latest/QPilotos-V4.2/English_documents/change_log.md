# CHANGELOG

This document records the major updates of **PilotOS (司南系统)** across different versions, helping users understand feature changes, improvements, and bug fixes.

------

# Contents

1. Version v4.1 - 2026-03-18
   - Added
   - Improvements
   - Fixes
   - Changes
2. Version v4.2 - 2026-04-29
   - Improvements

------

# Version v4.1 - 2026-03-18

## Added

- Added **MySQL and MongoDB connection test functionality**.
  During system startup, the script automatically checks database connectivity. If the connection test fails, the startup process will terminate with an error message to prevent the system from running under abnormal conditions.
- Added **startup validation mechanism for the PilotOS management service**.
  The management service verifies database connectivity upon startup to ensure all required dependencies are available.

## Improvements

- Optimized the **log output directory structure**.
  All system logs are now stored in a unified location for easier troubleshooting and feedback.

  Logs are located under the deployment directory:

  ```
  PilotOS-Log
  ```

  Users can check runtime logs and error messages in this directory.

## Fixes

- Fixed the issue where **documentation resources on the management homepage could not be accessed**, ensuring proper loading and availability.

## Changes

- Updated the **V20 chip topology structure** to a **20-qubit fully connected topology**, providing a more accurate representation of the current hardware capabilities.

------

# Version v4.2 - 2026-04-29

## Improvements

- Optimized the system management interface with **Chinese and English language support**.
- Enhanced the **variational computing service** to support **thread-safe multi-threaded access**.
- Improved **activation code verification responses** by adding error code fields.
- Optimized the **mapping algorithm** by introducing a **SWAP gate rollback mechanism**, ensuring successful mapping.
- Enhanced the variational computing service to support **mapping of variational circuit structures**.