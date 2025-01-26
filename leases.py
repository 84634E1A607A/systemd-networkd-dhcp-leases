#! /bin/python3

import dbus
import json
import traceback
import sys
import os

def get_interface_id(interface_name):
    """Retrieve the interface ID for a given interface name"""
    try:
        bus = dbus.SystemBus()

        service_name = "org.freedesktop.network1"
        object_path = "/org/freedesktop/network1"
        interface_name_manager = "org.freedesktop.network1.Manager"

        proxy = bus.get_object(service_name, object_path)

        link_path = proxy.GetLinkByName(interface_name, dbus_interface=interface_name_manager)

        return link_path[0]
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        exit(1)

def get_dhcp_leases(link_id):
    """Retrieve and parse DHCP dynamic leases"""
    try:
        bus = dbus.SystemBus()
        
        service_name = "org.freedesktop.network1"
        object_path = f"/org/freedesktop/network1/link/{link_id}"
        interface_name = "org.freedesktop.network1.DHCPServer"
        
        proxy = bus.get_object(service_name, object_path)
        
        leases_json = proxy.Get(interface_name, "Leases", dbus_interface="org.freedesktop.DBus.Properties")
        
        # Parse MAC and IP addresses
        leases = []
        for lease in leases_json:
            mac_bytes = lease[1][1:]
            ip_bytes = lease[2]
            
            mac_address = ":".join(f"{byte:02x}" for byte in mac_bytes)
            ip_address = ".".join(str(int(byte)) for byte in ip_bytes)
            
            leases.append({"MAC": mac_address, "IP": ip_address})
        
        return leases
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        exit(1)

def format_influxdb(interface_name, leases):
    """Format the DHCP leases in InfluxDB line protocol."""
    lines = []
    for lease in leases:
        mac_address = lease["MAC"]
        ip_address = lease["IP"]
        line = (
            f"systemd_networkd_dhcp_leases,"
            f"interface_name={interface_name},ip_address={ip_address} "
            f"mac_address=\"{mac_address}\",ip_address=\"{ip_address}\""
        )
        lines.append(line)
    return "\n".join(lines)

if __name__ == "__main__":
    if_name=os.getenv("INTERFACE")
    if if_name is None:
        print("Specify an interface with INTERFACE env", file=sys.stderr)
        exit(1)
    link_id = get_interface_id(if_name)
    leases = get_dhcp_leases(link_id)
    print(format_influxdb(if_name, leases))
