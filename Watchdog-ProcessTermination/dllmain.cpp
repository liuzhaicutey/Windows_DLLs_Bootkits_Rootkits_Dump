#include <windows.h>
#include <tlhelp32.h>
#include <set>
#include <string>
#include <fstream>

#define LOG_PATH L"C:\\procmon_log.txt" # debugger

void Log(const std::wstring& msg)
{
    std::wofstream f(LOG_PATH, std::ios::app);
    f << msg << std::endl;
}

std::set<DWORD> GetPIDs()
{
    std::set<DWORD> out;

    PROCESSENTRY32 pe;
    pe.dwSize = sizeof(pe);

    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE)
        return out;

    if (Process32First(snap, &pe))
    {
        do {
            out.insert(pe.th32ProcessID);
        } while (Process32Next(snap, &pe));
    }

    CloseHandle(snap);
    return out;
}

void KillProcess(DWORD pid)
{
    if (pid == GetCurrentProcessId())
        return; 

    HANDLE h = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
    if (!h)
    {
        Log(L"OpenProcess failed for PID " + std::to_wstring(pid));
        return;
    }

    if (TerminateProcess(h, 0))
        Log(L"KILLED PID " + std::to_wstring(pid));
    else
        Log(L"Terminate FAILED PID " + std::to_wstring(pid));

    CloseHandle(h);
}

DWORD WINAPI MonitorThread(LPVOID)
{
    Log(L"Monitor thread started");

    std::set<DWORD> known = GetPIDs();

    while (true)
    {
        auto now = GetPIDs();

        for (DWORD pid : now)
        {
            if (!known.count(pid))
            {
                Log(L"New PID detected: " + std::to_wstring(pid));
                KillProcess(pid);
            }
        }

        known = std::move(now);

        Sleep(100); 
    }
    return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls(hModule);

        CreateThread(nullptr, 0, MonitorThread, nullptr, 0, nullptr);
    }
    return TRUE;
}
