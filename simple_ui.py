#!/usr/bin/env python3
import sys
import os
import subprocess
import time

# --- Configuration ---
# The path to the proven, stable IK control script
ROARM_CONTROL_SCRIPT = "./roarm_control.py" 

def execute_move(x, y, z, r, g): 
    """
    Constructs and executes the proven roarm_control.py command using subprocess.
    This function accepts all five required parameters (X, Y, Z, R, G).
    """
    
    # Get the path to the Python executable currently running this script (usually inside .venv)
    python_executable = sys.executable 
    
    command = [
        python_executable, 
        ROARM_CONTROL_SCRIPT,
        "move",
        str(x),
        str(y),
        str(z),
        str(r),  # Roll (R)
        str(g)   # Gripper (G)
    ]
    
    print(f"\nExecuting: {' '.join(command)}")
    
    try:
        # Run the command, passing the current environment to ensure all modules (scipy, etc.) are found
        result = subprocess.run(command, capture_output=True, text=True, check=True, env=os.environ)
        print("\n--- Command Output ---")
        print(result.stdout)
        print("--- Move Complete ---")
        
    except subprocess.CalledProcessError as e:
        print(f"\n--- ERROR executing roarm_control.py ---")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        print("An error occurred during IK calculation or serial send. Check the output above for details.")
    except FileNotFoundError:
        print("\nFATAL ERROR: roarm_control.py not found. Ensure the script exists in the current directory.")

def get_user_input():
    """
    Prompts the user for all five movement parameters (X Y Z R G) on a single line, 
    matching your preferred command-line style.
    """
    
    print("\n--- Enter Target Coordinates (X Y Z R G) ---")
    print(" (X, Y, Z in mm; R, G in radians. Example: 250 0 150 0.0 3.0)")
    
    while True:
        try:
            # Read all five parameters from a single line
            user_line = input("X Y Z R G: ").strip()
            
            # Split the line by spaces and convert to a list of floats
            params = [float(p) for p in user_line.split()]
            
            if len(params) != 5:
                print(f"Error: Expected 5 parameters (X Y Z R G), but received {len(params)}.")
                continue
                
            x, y, z, r, g = params
            
            return x, y, z, r, g
            
        except ValueError:
            print("Invalid input format. Please ensure all 5 entries are valid numbers separated by spaces.")
            continue
        except KeyboardInterrupt:
            # Exit gracefully on Ctrl+C
            print("\nExiting interactive control.")
            sys.exit(0)

def main():
    print("--- RoArm Interactive XYZ Control ---")
    print(" (Press Ctrl+C to exit at any time)")

    while True:
        # Get all five parameters from the user
        x, y, z, r, g = get_user_input() 
        
        # Call the execute_move function with all five parameters
        execute_move(x, y, z, r, g) 
        time.sleep(0.5) 

if __name__ == "__main__":
    main()
