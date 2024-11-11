import subprocess
import sys
import time
import serial
import logging
from pathlib import Path
import winreg
import ctypes

class HuaweiE173Config:
    def __init__(self):
        self.logger = self._setup_logging()
        self.vendor_id = "12d1"  # Huawei vendor ID
        self.product_id = "140c"  # Initial product ID
        self.target_pid = "1436"  # Target modem mode product ID
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('modem_config.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger('HuaweiConfig')

    def send_at_command(self, port, command, wait_time=1):
        try:
            with serial.Serial(port, 9600, timeout=2) as ser:
                self.logger.info(f"Sending command to {port}: {command}")
                ser.write(f"{command}\r\n".encode())
                time.sleep(wait_time)
                response = ser.read_all().decode(errors='ignore')
                self.logger.info(f"Response: {response}")
                return response
        except Exception as e:
            self.logger.error(f"Error sending AT command: {e}")
            return None

    def find_modem_ports(self):
        """Find all potential modem COM ports based on keywords"""
        if sys.platform == "win32":
            import serial.tools.list_ports
            
            potential_ports = []
            ports = serial.tools.list_ports.comports()
            
            self.logger.info("Scanning for Huawei modem ports...")
            
            for port in ports:
                port_info = f"{port.device} {port.description} {port.hwid}".lower()
                self.logger.info(f"\nFound port:")
                self.logger.info(f"Device: {port.device}")
                self.logger.info(f"Description: {port.description}")
                self.logger.info(f"Hardware ID: {port.hwid}")
                
                # Only match Huawei devices
                if 'huawei' in port_info or 'vid_12d1' in port_info:
                    self.logger.info(f"Found Huawei device on port {port.device}")
                    potential_ports.append(port.device)
                else:
                    self.logger.info(f"Skipping non-Huawei port {port.device}")
                    
            self.logger.info(f"Found {len(potential_ports)} Huawei modem ports: {potential_ports}")
            return potential_ports

        return []

    def modify_windows_registry(self):
        """Modify Windows registry to prevent CD-ROM detection"""
        try:
            # Disable USBSTOR
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SYSTEM\CurrentControlSet\Services\USBSTOR",
                               0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 4)
            
            # Disable AutoRun
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SYSTEM\CurrentControlSet\Services\cdrom",
                               0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "AutoRun", 0, winreg.REG_DWORD, 0)
            return True
        except Exception as e:
            self.logger.error(f"Registry modification failed: {e}")
            return False

    def send_usb_control_message(self):
        """Send USB control message to switch mode"""
        try:
            import usb.core
            import usb.util
            
            dev = usb.core.find(idVendor=0x12d1, idProduct=int(self.product_id, 16))
            if dev is None:
                self.logger.error("Device not found")
                return False
                
            # Standard USB mode switch message for E173
            message = bytes.fromhex("55534243123456780000000000000011062000000100000000000000000000")
            
            try:
                dev.ctrl_transfer(0x21, 0x20, 0, 0, message)
                time.sleep(3)  # Wait for device to switch
                return True
            except Exception as e:
                self.logger.error(f"Control transfer failed: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"USB control message failed: {e}")
            return False

    def try_configure_port(self, port):
        """Attempt to configure a specific port"""
        try:
            self.logger.info(f"\nAttempting to configure port: {port}")
            
            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=self.baud_rate if hasattr(self, 'baud_rate') else 9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=3
                )
            except serial.SerialException as e:
                self.logger.error(f"Could not open {port}: {str(e)}")
                return False

            if not ser.is_open:
                self.logger.error(f"Could not open {port}")
                return False

            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                # Enhanced command sets with all known commands
                command_sets = [
                    # Set 1: Advanced configuration with unlock
                    [
                        ("AT^DATALOCK=\"A2D2C2E2\"", "OK", 3),  # Unlock advanced settings
                        ("AT^U2DIAG=0", "OK", 3),  # Disable CD-ROM
                        ("AT^SETPORT=\"FF;12,10,16\"", "OK", 3),  # Force modem mode
                        ("AT^CARDMODE=2", "OK", 3),  # Force modem mode
                        ("AT+CFUN=1,1", "OK", 3),  # Reset device
                    ],
                    # Set 2: Standard configuration
                    [
                        ("AT+CFUN=0", "OK", 3),  # Reset device
                        ("AT^SETPORT=A1,A2", "OK", 3),  # Set ports to modem mode
                        ("AT^U2DIAG=0", "OK", 3),  # Disable CD-ROM
                        ("AT^RESET", "OK", 3),  # Hard reset
                    ],
                    # Set 3: Alternative port configuration
                    [
                        ("AT^SETPORT=\"1,2,3,4\"", "OK", 3),  # Alternative port config
                        ("AT^U2DIAG=256", "OK", 3),  # Alternative CD-ROM disable
                        ("AT+CFUN=1,1", "OK", 3),  # Reset device
                    ],
                    # Set 4: Minimal configuration
                    [
                        ("AT^U2DIAG=0", "OK", 3),
                        ("AT+CFUN=1", "OK", 3),
                    ]
                ]

                # Try each command set
                for command_set in command_sets:
                    success = True
                    self.logger.info(f"\nTrying command set on {port}:")
                    
                    for cmd, expected_response, timeout in command_set:
                        self.logger.info(f"\nSending command: {cmd}")
                        ser.reset_input_buffer()
                        ser.write(f"{cmd}\r\n".encode())
                        
                        total_response = ""
                        start_time = time.time()
                        
                        while (time.time() - start_time) < timeout:
                            if ser.in_waiting:
                                chunk = ser.read_all().decode(errors='ignore')
                                total_response += chunk
                                self.logger.info(f"Received chunk: {chunk}")
                                
                                if expected_response in total_response:
                                    break
                            time.sleep(0.1)
                        
                        self.logger.info(f"Final response: {total_response}")
                        
                        if expected_response not in total_response:
                            success = False
                            break
                        
                        time.sleep(1)
                    
                    if success:
                        ser.close()
                        return True
                    
                    time.sleep(2)
                
                ser.close()
                return False

            except Exception as e:
                self.logger.error(f"Error configuring {port}: {str(e)}")
                if ser.is_open:
                    ser.close()
                return False

        except Exception as e:
            self.logger.error(f"Error in try_configure_port for {port}: {str(e)}")
            return False

    def switch_to_modem_mode(self):
        """Try all available methods to switch the modem"""
        try:
            # 1. Try registry modification first
            self.logger.info("Attempting registry modification...")
            self.modify_windows_registry()
            time.sleep(2)

            # 2. Try USB control message
            self.logger.info("Attempting USB mode switch...")
            if self.send_usb_control_message():
                time.sleep(3)  # Wait for device to reset

            # 3. Try AT commands on all potential ports
            potential_ports = self.find_modem_ports()
            
            if not potential_ports:
                self.logger.error("No potential modem ports found")
                return False

            self.logger.info(f"Found {len(potential_ports)} potential ports to try")
            
            for port in potential_ports:
                if self.try_configure_port(port):
                    self.logger.info(f"Successfully configured modem on port {port}")
                    return True
                else:
                    self.logger.info(f"Failed to configure port {port}, trying next port...")
                    time.sleep(1)
            
            self.logger.error("Failed to configure any ports")
            return False

        except Exception as e:
            self.logger.error(f"Error in switch_to_modem_mode: {e}")
            return False

    def save_configuration(self):
        """Save the current configuration to persist across reboots"""
        try:
            # If we have a manual port that worked, use it
            if hasattr(self, 'manual_port'):
                port = self.manual_port
            else:
                # Otherwise try to find a working port
                potential_ports = self.find_modem_ports()
                if not potential_ports:
                    self.logger.error("No modem ports found for saving configuration")
                    return False
                port = potential_ports[0]  # Try the first potential port

            self.logger.info(f"Attempting to save configuration on port {port}")
            
            # Save settings and reset device
            commands = [
                "AT&W",  # Save settings
                "AT+CFUN=1,1"  # Reset device
            ]
            
            success = True
            for cmd in commands:
                response = self.send_at_command(port, cmd, wait_time=2)
                if not response or "ERROR" in response:
                    self.logger.error(f"Failed to execute {cmd} on {port}")
                    success = False
                    break
                time.sleep(2)
            
            return success

        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False