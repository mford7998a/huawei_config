import subprocess
import sys
import time
import serial
import logging
from pathlib import Path

class HuaweiE173Config:
    def __init__(self):
        self.logger = self._setup_logging()
        self.vendor_id = "12d1"  # Huawei vendor ID
        self.product_id = "140c"  # Your device's current product ID
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

    def find_modem_port(self):
        """Find the COM port for the modem"""
        if sys.platform == "win32":
            import serial
            import serial.tools.list_ports
            
            # If manual port is specified, try it first
            if hasattr(self, 'manual_port') and self.manual_port:
                self.logger.info(f"Using manually specified port: {self.manual_port}")
                try:
                    # Add error handling for port access
                    try:
                        ser = serial.Serial(
                            port=self.manual_port,
                            baudrate=9600,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=1,
                            xonxoff=False,
                            rtscts=False,
                            dsrdtr=False
                        )
                    except serial.SerialException as e:
                        self.logger.error(f"Failed to open {self.manual_port}: {str(e)}")
                        return None

                    if ser.is_open:
                        self.logger.info(f"Successfully opened {self.manual_port}")
                        try:
                            # Clear any pending data
                            ser.reset_input_buffer()
                            ser.reset_output_buffer()
                            
                            # Send AT command
                            ser.write(b"AT\r\n")
                            time.sleep(1)
                            
                            # Read response
                            response = ser.read_all()
                            if response:
                                self.logger.info(f"Port {self.manual_port} responded: {response}")
                                ser.close()
                                return self.manual_port
                            else:
                                self.logger.info(f"No response from {self.manual_port}")
                        except Exception as e:
                            self.logger.error(f"Error communicating with port: {str(e)}")
                        finally:
                            ser.close()
                    else:
                        self.logger.error(f"Could not open {self.manual_port}")
                except Exception as e:
                    self.logger.error(f"Error with manual port: {str(e)}")
                    return None

            # Fall back to auto-detection if manual port fails or isn't specified
            ports = serial.tools.list_ports.comports()
            
            self.logger.info("Scanning for modem ports...")
            self.logger.info(f"Looking for VID_{self.vendor_id} and PID_{self.product_id}")
            
            for port in ports:
                self.logger.info(f"\nPort details:")
                self.logger.info(f"Device: {port.device}")
                self.logger.info(f"Description: {port.description}")
                self.logger.info(f"Hardware ID: {port.hwid}")
                
                # More permissive check for Huawei device
                if "VID_12D1" in port.hwid:
                    self.logger.info(f"Found Huawei device on {port.device}")
                    try:
                        ser = serial.Serial(
                            port=port.device,
                            baudrate=9600,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=1
                        )
                        
                        if ser.is_open:
                            ser.write(b"AT\r\n")
                            time.sleep(1)
                            response = ser.read_all()
                            ser.close()
                            
                            if response:
                                self.logger.info(f"Port {port.device} responded to AT command")
                                return port.device
                            else:
                                self.logger.info(f"No response from {port.device}")
                    except Exception as e:
                        self.logger.info(f"Could not open {port.device}: {str(e)}")
                        continue
            
            self.logger.error("No responsive modem port found")
            return None

    def switch_to_modem_mode(self):
        """Switch the device to modem-only mode"""
        try:
            # Try multiple times to find the port
            max_attempts = 3
            port = None
            
            for attempt in range(max_attempts):
                self.logger.info(f"Attempt {attempt + 1} to find modem port...")
                port = self.find_modem_port()
                if port:
                    break
                time.sleep(2)  # Wait before retry
            
            if not port:
                self.logger.error(f"No modem port found after {max_attempts} attempts")
                return False

            self.logger.info(f"Found modem on port {port}")
            
            # Try different command sets
            command_sets = [
                # First set - Standard commands
                [
                    "AT+CFUN=1",
                    "AT^SETPORT=A1,A2",
                    "AT^U2DIAG=0",
                ],
                # Second set - Alternative commands
                [
                    "AT^SETPORT=1,0",
                    "AT^SYSCFG=13,1,3FFFFFFF,2,4",
                    "AT+CFUN=1",
                ],
                # Third set - Minimal commands
                [
                    "AT+CFUN=1",
                    "AT^U2DIAG=0",
                ]
            ]

            for command_set in command_sets:
                self.logger.info(f"Trying command set: {command_set}")
                success = True
                
                for cmd in command_set:
                    response = self.send_at_command(port, cmd, wait_time=2)
                    self.logger.info(f"Command: {cmd} -> Response: {response}")
                    
                    if not response or "ERROR" in response:
                        self.logger.error(f"Failed with command: {cmd}")
                        success = False
                        break
                    time.sleep(1)
                
                if success:
                    self.logger.info("Successfully configured modem")
                    return True
                    
                self.logger.info("Command set failed, trying next set...")
                time.sleep(2)

            self.logger.error("All command sets failed")
            return False

        except Exception as e:
            self.logger.error(f"Error configuring modem: {e}")
            return False

    def save_configuration(self):
        """Save the current configuration to persist across reboots"""
        port = self.find_modem_port()
        if port:
            # Save settings and reset device
            commands = [
                "AT&W",  # Save settings
                "AT+CFUN=1,1"  # Reset device
            ]
            for cmd in commands:
                self.send_at_command(port, cmd)
                time.sleep(2)
            return True
        return False