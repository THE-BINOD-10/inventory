using System;
using System.Collections.Generic;
using System.Windows.Forms;

namespace TallyBridgeApp
{
    public static class Program
    {
        public static TallyBridgeTest tallyBridger;
        /// <summary>
        /// The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            tallyBridger = new TallyBridgeTest();
            Application.Run(tallyBridger);
        }
    }
}