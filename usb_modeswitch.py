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

    def find_modem_ports(self):
        """Find all potential modem COM ports based on keywords"""
        if sys.platform == "win32":
            import serial.tools.list_ports
            
            # Keywords that might indicate a Huawei modem port
            keywords = [
                'huawei',
                'mobile',
                'modem',
                'com port',
                'serial',
                'VID_12D1',  # Huawei Vendor ID
                'USB Serial'
            ]
            
            potential_ports = []
            ports = serial.tools.list_ports.comports()
            
            self.logger.info("Scanning for potential modem ports...")
            
            for port in ports:
                port_info = f"{port.device} {port.description} {port.hwid}".lower()
                self.logger.info(f"\nFound port:")
                self.logger.info(f"Device: {port.device}")
                self.logger.info(f"Description: {port.description}")
                self.logger.info(f"Hardware ID: {port.hwid}")
                
                # Check if any keyword matches
                if any(keyword.lower() in port_info for keyword in keywords):
                    self.logger.info(f"Port {port.device} matches keywords")
                    potential_ports.append(port.device)
                
            self.logger.info(f"Found {len(potential_ports)} potential modem ports: {potential_ports}")
            return potential_ports

        return []

    def try_configure_port(self, port):
        """Attempt to configure a specific port"""
        try:
            self.logger.info(f"\nAttempting to configure port: {port}")
            
            # Try to open the port
            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=self.baud_rate if hasattr(self, 'baud_rate') else 9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
            except serial.SerialException as e:
                self.logger.error(f"Could not open {port}: {str(e)}")
                return False

            if not ser.is_open:
                self.logger.error(f"Could not open {port}")
                return False

            try:
                # Test AT command
                ser.write(b"AT\r\n")
                time.sleep(1)
                response = ser.read_all()
                
                if not response:
                    self.logger.info(f"No response from {port}")
                    ser.close()
                    return False

                self.logger.info(f"Port {port} responded to AT command")
                
                # Try command sets
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
                    success = True
                    self.logger.info(f"Trying command set on {port}: {command_set}")
                    
                    for cmd in command_set:
                        ser.write(f"{cmd}\r\n".encode())
                        time.sleep(2)
                        response = ser.read_all().decode(errors='ignore')
                        self.logger.info(f"Command: {cmd} -> Response: {response}")
                        
                        if not response or "ERROR" in response:
                            success = False
                            break
                    
                    if success:
                        self.logger.info(f"Successfully configured port {port}")
                        ser.close()
                        return True
                    
                    self.logger.info("Command set failed, trying next set...")
                    time.sleep(1)
                
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
        """Try to configure all potential modem ports"""
        try:
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