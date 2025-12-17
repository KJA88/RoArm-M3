# 🛸 RoArm-M3 & Raspberry Pi Troubleshooting Master Log

## **1. Network & Connection (The "OfflineError" Fix)**
* **Find the REAL IP:** Plug a monitor into the Pi and run `hostname -I`.
* **IP Hopping:** Be aware that the Pi may switch between `192.168.4.2` (Arm Hotspot) and `192.168.1.x` (Home WiFi).
* **Update VS Code:** Modify `C:\Users\Admin...\.ssh\config` to match the current IP.
* **SSH Config Entry:**
    ```text
    Host RoArm
      HostName [CURRENT_IP]
      User kallen
    ```

## **2. SSH Protocol (The "kallen" Settings)**
* **Correct User:** Always use `kallen`, never `pi`.
* **Security Settings:** Ensure `/etc/ssh/sshd_config` includes:
    * `PasswordAuthentication yes`
    * `PubkeyAuthentication yes`
* **Clean Config:** Remove any "stray characters" or corrupted lines in `sshd_config`.
* **Password Force:** Use `sudo passwd kallen` to reset if authentication fails.
* **Service Restart:** Run `sudo systemctl restart ssh` after any changes.

## **3. Hardware & Serial (The "Lidar Trap")**
* **Wrong Interface:** Do not connect to the LiDAR data interface for programming; use the ESP32 serial interface.
* **Identify Port:** Use `ls /dev/ttyUSB*` before and after plugging in to find the correct device (usually `ttyUSB0` or `ttyUSB1`).
* **Power:** Watch for the "Yellow Lightning Bolt" on the Pi monitor indicating under-voltage when the arm moves.

## **4. Quick Recovery Checklist**
1. Get IP: `hostname -I`.
2. Verify SSH: `sudo systemctl status ssh`.
3. Check User: Use `kallen`.
4. Verify Port: Confirm ESP32 USB, not LiDAR.
