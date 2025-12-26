import google.generativeai as genai
import yaml
import os
from agent_tools import GDBInterface
from hardware_oracle import HardwareOracle

# 1. Setup Gemini
# Ensure you have your API key set in the environment or replace this string
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY"))

# --- Load Device Configuration ---
try:
    with open("config.yaml", "r") as f:
        device_config = yaml.safe_load(f)
    print("Loaded device configuration.")
except FileNotFoundError:
    print("Warning: config.yaml not found. Agent will not have memory map context.")
    device_config = {}

# --- Initialize Hardware Oracle ---
# We assume the user has an SVD file. If not, we'll warn but continue.
svd_path = "firmware/device.svd" # Placeholder path
oracle = None
if os.path.exists(svd_path):
    try:
        oracle = HardwareOracle(svd_path)
        print(f"Loaded SVD file: {svd_path}")
    except Exception as e:
        print(f"Failed to load SVD: {e}")
else:
    print(f"SVD file not found at {svd_path}. Hardware Oracle tools will be limited.")

# Initialize the interface globally so we can pass bound methods to Gemini
gdb_interface = GDBInterface("firmware/app.elf")

# 2. Define the tools for Gemini
tools = [
    gdb_interface.get_registers,
    gdb_interface.read_memory,
    gdb_interface.step_instruction,
    gdb_interface.continue_execution,
    gdb_interface.set_breakpoint,
    gdb_interface.backtrace,
    gdb_interface.evaluate_expression,
    gdb_interface.restart_environment,
    gdb_interface.write_register,
    gdb_interface.write_memory
]

# Add Oracle tools if available
if oracle:
    tools.append(oracle.resolve_address)
    tools.append(oracle.get_reg_info)

# --- Create System Instruction with Context ---
system_instruction = f"""
You are an autonomous embedded debugging agent connected to a GDB session.
Your goal is to diagnose firmware issues by inspecting registers, memory, and execution flow.

DEVICE CONTEXT:
The following is the memory map and register definition for the target device. 
Use these addresses when the user asks about specific peripherals (e.g., "Check GPIOA").
{yaml.dump(device_config)}

GUIDELINES:
1. Always check if a peripheral clock is enabled (RCC registers) before checking the peripheral itself.
2. If you read a register, explain what the bit values mean based on standard ARM/MCU conventions.
3. Use 'read_memory' for peripheral registers and 'get_registers' for CPU core registers (R0-R15).
4. Use 'resolve_address' to interpret raw memory addresses you encounter.
5. Use 'get_reg_info' to find the address of a register by name if it's not in the YAML config.
"""

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash', 
    tools=tools,
    system_instruction=system_instruction
)

# 3. Start the Chat with History (Enables Memory)
chat = model.start_chat(enable_automatic_function_calling=True)

def run_agent():
    # Start the GDB/QEMU session
    print("Starting GDB Environment...")
    gdb_interface.start()
    
    print("JTAG Agent Ready. Ask a question about your device.")
    while True:
        user_input = input("User > ")
        if user_input.lower() in ["exit", "quit"]: 
            gdb_interface.stop_all()
            break
        
        try:
            # Gemini will automatically call tools if it needs data from GDB
            response = chat.send_message(user_input)
            print(f"Agent > {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_agent()