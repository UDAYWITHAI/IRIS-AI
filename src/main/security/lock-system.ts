import { ipcMain } from 'electron'

export default function registerLockSystem() {
  ipcMain.on('trigger-lockdown', (event) => {
    console.log('🔒 TACTICAL LOCKDOWN INITIATED VIA AI.')
    // This physically reloads the Electron WebContents. 
    // It instantly clears RAM, drops the AI connection, and remounts the Vault Door.
    event.sender.reload()
  })
}