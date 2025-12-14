# Manual PE Mapper

A **custom in-memory PE file loader**, this utility is designed to map a **PE (Portable Executable)** file into memory, modify the necessary data structures, and prepare it for execution. This technique is commonly used in scenarios such as **reflective DLL injection**, **packing and unpacking executables**, **obfuscation**, and **custom anti-debugging** mechanisms. You can use it to directly load a PE file into your application or inject it into a target process.

---

## Key Operations & Workflow

The code follows four key stages to load and execute a PE file in memory:

### 1. Memory Allocation & Copying:
   - Uses **`VirtualAlloc`** to allocate memory at the PE file's preferred base address (or a new base if ASLR is involved).
   - Copies the headers, sections (e.g., `.text`, `.data`), and other necessary parts of the PE file into the newly allocated memory using **`memcpy`**.

### 2. Import Resolution (Linking):
   - The **`ProcessImports`** function parses the PE file's Import Directory to find external dependencies (DLLs and functions).
   - It uses **`LoadLibraryA`** to load the required DLLs and **`GetProcAddress`** to dynamically resolve function addresses. These addresses are written into the new image’s Import Address Table (IAT), allowing the PE file to access external functions at runtime.

### 3. Relocation Fix-up:
   - If the PE file is loaded at a different base address than the preferred one (due to ASLR), all absolute addresses and pointers inside the file need to be updated.
   - The **`ProcessRelocations`** function processes the **IMAGE_BASE_RELOCATION** directory and adjusts the pointers by adding the base address difference (delta), ensuring the internal references are valid.

### 4. Execution Preparation:
   - **`VirtualProtect`** is used to set appropriate memory protections (e.g., **Read**, **Write**, **Execute**) on the newly allocated memory, ensuring it’s ready for execution.
   - It handles any **Thread Local Storage (TLS) callbacks** that may need to be executed during initialization.
   - Finally, the tool identifies the new entry point of the program and transfers control to it, initiating the execution of the reassembled module.

---

## Important Considerations

- **ASLR (Address Space Layout Randomization):** If the PE file is being relocated due to ASLR, make sure to account for this when mapping the image and fixing relocations.
- **Error Handling:** The code assumes that operations like `VirtualAlloc`, `memcpy`, and `VirtualProtect` succeed. You should implement robust error handling to ensure the program handles failure cases gracefully.
- **TLS Callbacks:** The `ExecuteTLSCallbacks` function is responsible for running any initialization code defined in the TLS section of the PE file. These are crucial for DLLs but may not be used in all PE files.
- **Import Address Table (IAT):** Be sure to resolve all dynamic imports correctly, including **delayed imports**, which may require special handling.

---

## DISCLAIMER

The techniques outlined in this repository can be useful for educational purposes, reverse engineering, and legitimate software development. However, **misuse of these techniques for malicious purposes**, such as unauthorized code injection, tampering with system processes, or evading security mechanisms, is illegal and unethical. Always ensure that you have the proper permissions and comply with local laws and regulations when using this code.

The author is not responsible for any damage, data loss, or legal consequences arising from the use or misuse of this material.

---

## Contacts

For further inquiries, you can reach the author at:  
[Telegram: Shaacidyne](https://t.me/Shaacidyne)
