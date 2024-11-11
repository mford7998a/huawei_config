import sys
from usb_modeswitch import HuaweiE173Config
import serial.tools.list_ports

def main():
    config = HuaweiE173Config()
    
    print("Huawei Modem Configuration Tool")
    print("-------------------------------")
    print("Detected ports:")
    
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"\nPort: {port.device}")
        print(f"Description: {port.description}")
        print(f"Hardware ID: {port.hwid}")
    
    # Add manual port selection
    print("\nSelect an option:")
    print("1. Auto-detect modem port")
    print("2. Manually enter COM port")
    
    choice = input("Enter choice (1 or 2): ")
    
    if choice == "2":
        port_num = input("Enter COM port number (e.g., 930): ")
        config.manual_port = f"COM{port_num}"
        
        print("\nSelect baud rate:")
        print("1. 9600 (default)")
        print("2. 115200")
        print("3. 57600")
        print("4. 38400")
        
        baud_choice = input("Enter choice (1-4): ")
        baud_rates = {
            "1": 9600,
            "2": 115200,
            "3": 57600,
            "4": 38400
        }
        config.baud_rate = baud_rates.get(baud_choice, 9600)
    else:
        config.manual_port = None
        config.baud_rate = 9600
    
    print("\nAttempting to configure modem...")
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