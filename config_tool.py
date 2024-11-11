import sys
import serial.tools.list_ports
from usb_modeswitch import HuaweiE173Config

def list_available_ports():
    """Display all available COM ports"""
    print("\nAvailable ports:")
    ports = serial.tools.list_ports.comports()
    for i, port in enumerate(ports, 1):
        print(f"\n{i}. Port: {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Hardware ID: {port.hwid}")
    return ports

def main():
    config = HuaweiE173Config()
    
    print("Huawei Modem Configuration Tool")
    print("-------------------------------")
    
    print("\nSelect operation mode:")
    print("1. Automatic port detection and configuration")
    print("2. Manual port selection")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "2":
        ports = list(list_available_ports())
        if not ports:
            print("No COM ports found!")
            sys.exit(1)
            
        while True:
            try:
                port_num = input("\nEnter port number (or 'q' to quit): ").strip()
                if port_num.lower() == 'q':
                    sys.exit(0)
                    
                port_idx = int(port_num) - 1
                if 0 <= port_idx < len(ports):
                    config.manual_port = ports[port_idx].device
                    break
                else:
                    print("Invalid port number!")
            except ValueError:
                print("Please enter a valid number!")
        
        print(f"\nAttempting to configure port {config.manual_port}...")
    else:
        print("\nScanning for modem ports...")
    
    if config.switch_to_modem_mode():
        print("\nSuccessfully configured modem to SMS-only mode")
        
        if config.save_configuration():
            print("Configuration saved permanently")
        else:
            print("Warning: Could not save configuration permanently")
            
        print("\nConfiguration complete. You can now use the modem for SMS")
    else:
        print("\nError: Failed to configure modem")
        print("Please check modem_config.log for detailed information")
        sys.exit(1)

if __name__ == "__main__":
    main() 