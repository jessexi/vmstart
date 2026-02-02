import Virtualization
import Foundation

// Configuration - 支持通过环境变量覆盖默认值
let diskPath = ProcessInfo.processInfo.environment["VMCTL_DISK"] ?? "ubuntu.raw"
let seedPath = ProcessInfo.processInfo.environment["VMCTL_SEED"] ?? "seed.iso"
let efiVarStorePath = ProcessInfo.processInfo.environment["VMCTL_EFI_STORE"] ?? "efi_vars.store"
let machineIdPath = ProcessInfo.processInfo.environment["VMCTL_MACHINE_ID"] ?? "machine_id.bin"

// CPU和内存配置
let cpuCount = Int(ProcessInfo.processInfo.environment["VMCTL_CPU"] ?? "") ?? 2
let memorySize = UInt64(ProcessInfo.processInfo.environment["VMCTL_MEMORY"] ?? "") ?? (2 * 1024 * 1024 * 1024)
let vmName = ProcessInfo.processInfo.environment["VMCTL_NAME"] ?? "default"

func createVirtualMachine() -> VZVirtualMachine? {
    // Check if disk exists
    guard FileManager.default.fileExists(atPath: diskPath) else {
        print("Error: Disk image '\(diskPath)' not found.")
        print("Please convert the QCOW2 image to RAW format: qemu-img convert -f qcow2 -O raw ubuntu-24.04-server-cloudimg-amd64.img ubuntu.raw")
        return nil
    }

    let config = VZVirtualMachineConfiguration()
    config.cpuCount = cpuCount
    config.memorySize = memorySize

    // Boot Loader (EFI)
    let bootLoader = VZEFIBootLoader()
    let efiVariableStore: VZEFIVariableStore
    do {
        if FileManager.default.fileExists(atPath: efiVarStorePath) {
            efiVariableStore = VZEFIVariableStore(url: URL(fileURLWithPath: efiVarStorePath))
        } else {
            efiVariableStore = try VZEFIVariableStore(creatingVariableStoreAt: URL(fileURLWithPath: efiVarStorePath))
        }
    } catch {
        print("Failed to create EFI variable store: \(error)")
        return nil
    }
    bootLoader.variableStore = efiVariableStore
    config.bootLoader = bootLoader

    // Platform (Generic)
    let platform = VZGenericPlatformConfiguration()
    let machineIdentifier: VZGenericMachineIdentifier
    if FileManager.default.fileExists(atPath: machineIdPath),
       let data = try? Data(contentsOf: URL(fileURLWithPath: machineIdPath)),
       let id = VZGenericMachineIdentifier(dataRepresentation: data) {
        machineIdentifier = id
    } else {
        machineIdentifier = VZGenericMachineIdentifier()
        try? machineIdentifier.dataRepresentation.write(to: URL(fileURLWithPath: machineIdPath))
    }
    platform.machineIdentifier = machineIdentifier
    config.platform = platform

    // Storage: Main Disk
    if let diskAttachment = try? VZDiskImageStorageDeviceAttachment(url: URL(fileURLWithPath: diskPath), readOnly: false) {
        let diskParams = VZVirtioBlockDeviceConfiguration(attachment: diskAttachment)
        config.storageDevices.append(diskParams)
    } else {
        print("Failed to attach disk image.")
        return nil
    }

    // Storage: Seed ISO
    if FileManager.default.fileExists(atPath: seedPath),
       let seedAttachment = try? VZDiskImageStorageDeviceAttachment(url: URL(fileURLWithPath: seedPath), readOnly: true) {
        let seedParams = VZVirtioBlockDeviceConfiguration(attachment: seedAttachment)
        config.storageDevices.append(seedParams)
    }

    // Network (NAT)
    let natAttachment = VZNATNetworkDeviceAttachment()
    let network = VZVirtioNetworkDeviceConfiguration()
    network.attachment = natAttachment
    if let mac = VZMACAddress(string: "02:00:00:00:00:01") {
        network.macAddress = mac
    }
    config.networkDevices = [network]

    // Console (Serial)
    let serialAttachment = VZFileHandleSerialPortAttachment(
        fileHandleForReading: FileHandle.standardInput,
        fileHandleForWriting: FileHandle.standardOutput
    )
    let serial = VZVirtioConsoleDeviceSerialPortConfiguration()
    serial.attachment = serialAttachment
    config.serialPorts = [serial]
    
    // Entropy
    config.entropyDevices = [VZVirtioEntropyDeviceConfiguration()]
    
    // Input Devices (Keyboard/Pointing) - Optional but good for GUI logic if we had one
    config.keyboards = [VZUSBKeyboardConfiguration()]
    config.pointingDevices = [VZUSBScreenCoordinatePointingDeviceConfiguration()]

    do {
        try config.validate()
        return VZVirtualMachine(configuration: config, queue: .main)
    } catch {
        print("Invalid config: \(error)")
        return nil
    }
}

class VMDelegate: NSObject, VZVirtualMachineDelegate {
    func guestDidStop(_ virtualMachine: VZVirtualMachine) {
        print("Guest stopped.")
        exit(0)
    }
    
    func virtualMachine(_ virtualMachine: VZVirtualMachine, didStopWithError error: Error) {
        print("Guest stopped with error: \(error)")
        exit(1)
    }
}

// Main Execution
guard let vm = createVirtualMachine() else {
    exit(1)
}

let delegate = VMDelegate()
vm.delegate = delegate

print("Starting VM '\(vmName)'...")
print("  Disk: \(diskPath)")
print("  CPU: \(cpuCount) cores")
print("  Memory: \(memorySize / 1024 / 1024)MB")
vm.start { result in
    switch result {
    case .success:
        print("VM Started. Console output will appear below.")
    case .failure(let error):
        print("Failed to start: \(error)")
        exit(1)
    }
}

RunLoop.main.run()
