using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

namespace ArbitrumUpdater
{
    class Program
    {
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool DeleteFile(string name);

        static void Main(string[] args)
        {
            // Args:
            // args[0] = parent PID to wait for
            // args[1] = new downloaded exe path
            // args[2] = target current exe path

            if (args.Length < 3)
            {
                return;
            }

            int pid;
            int.TryParse(args[0], out pid);
            string newExe = args[1];
            string curExe = args[2];

            // 1. Ожидаем полного закрытия основного процесса
            if (pid > 0)
            {
                try
                {
                    Process parentProc = Process.GetProcessById(pid);
                    if (!parentProc.HasExited)
                    {
                        parentProc.WaitForExit(10000);
                    }
                }
                catch
                {
                    // Процесс уже завершился
                }
            }

            // Дополнительная пауза для сброса всех файловых дескрипторов и SmartScreen
            Thread.Sleep(800);

            // 2. Снимаем метку скачивания из интернета (Zone.Identifier)
            try
            {
                string zoneFile = newExe + ":Zone.Identifier";
                DeleteFile(zoneFile);
            }
            catch { }

            // 3. Заменяем целевой exe
            bool replaced = false;
            for (int i = 0; i < 30; i++)
            {
                try
                {
                    File.Copy(newExe, curExe, true);
                    replaced = true;
                    break;
                }
                catch
                {
                    Thread.Sleep(300);
                }
            }

            // Удаляем временный файл обновления
            try
            {
                if (File.Exists(newExe))
                {
                    File.Delete(newExe);
                }
            }
            catch { }

            // 4. Снимаем метку интернета с самого замененного файла перед запуском
            try
            {
                string targetZone = curExe + ":Zone.Identifier";
                DeleteFile(targetZone);
            }
            catch { }

            // 5. Запускаем обновленное приложение
            if (replaced && File.Exists(curExe))
            {
                Thread.Sleep(500);
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo();
                    psi.FileName = curExe;
                    psi.WorkingDirectory = Path.GetDirectoryName(curExe);
                    psi.UseShellExecute = true;
                    Process.Start(psi);
                }
                catch { }
            }
        }
    }
}
