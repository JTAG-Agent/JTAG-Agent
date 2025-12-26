import os
from cmsis_svd.parser import SVDParser

class HardwareOracle:
    def __init__(self, svd_path):
        """
        Initializes the HardwareOracle with an SVD file.
        
        Args:
            svd_path (str): Path to the .svd file.
        """
        if not os.path.exists(svd_path):
            raise FileNotFoundError(f"SVD file not found at: {svd_path}")
            
        self.parser = SVDParser.for_xml_file(svd_path)
        self.device = self.parser.get_device()
        
        # Cache for faster lookups could be added here, 
        # but for now we'll iterate since SVDs aren't massive.
        self.peripherals = self.device.peripherals

    def resolve_address(self, hex_addr: str):
        """
        Identifies the peripheral, register, and fields for a given memory address.
        
        Args:
            hex_addr (str): The address in hex string format (e.g., "0x40023800").
            
        Returns:
            dict: Information about the address or None if not found.
        """
        try:
            addr = int(hex_addr, 16)
        except ValueError:
            return {"error": f"Invalid address format: {hex_addr}"}

        for periph in self.peripherals:
            # Check if address is within this peripheral's potential range
            # SVDs don't always define a strict size, so we often check base + register offsets
            # But usually, peripherals are 1KB or 4KB blocks.
            # A safer way is to check if addr >= base_address
            
            base = periph.base_address
            
            # Optimization: If address is clearly outside, skip (assuming sorted, but they might not be)
            # We'll just check if the address matches any register in this peripheral
            
            # Calculate offset
            if addr < base:
                continue
                
            offset = addr - base
            
            # Search registers
            for reg in periph.registers:
                if reg.address_offset == offset:
                    # Found a match!
                    fields = []
                    for f in reg.fields:
                        fields.append({
                            "name": f.name,
                            "bit_offset": f.bit_offset,
                            "bit_width": f.bit_width,
                            "description": f.description
                        })
                        
                    return {
                        "peripheral": periph.name,
                        "register": reg.name,
                        "description": reg.description,
                        "address": hex(addr),
                        "fields": fields
                    }
        
        return {"status": "No matching register found for this address."}

    def get_reg_info(self, name: str):
        """
        Returns address information for a peripheral or specific register.
        
        Args:
            name (str): Name of peripheral (e.g. "GPIOA") or register (e.g. "GPIOA.MODER").
            
        Returns:
            dict: Address details.
        """
        parts = name.upper().split('.')
        p_name = parts[0]
        r_name = parts[1] if len(parts) > 1 else None
        
        found_periph = None
        for p in self.peripherals:
            if p.name == p_name:
                found_periph = p
                break
        
        if not found_periph:
            return {"error": f"Peripheral '{p_name}' not found."}
            
        if r_name:
            for r in found_periph.registers:
                if r.name == r_name:
                    return {
                        "peripheral": p_name,
                        "register": r_name,
                        "base_address": hex(found_periph.base_address),
                        "offset": hex(r.address_offset),
                        "absolute_address": hex(found_periph.base_address + r.address_offset),
                        "description": r.description
                    }
            return {"error": f"Register '{r_name}' not found in '{p_name}'."}
        else:
            return {
                "peripheral": p_name,
                "base_address": hex(found_periph.base_address),
                "description": found_periph.description,
                "registers": [r.name for r in found_periph.registers]
            }
