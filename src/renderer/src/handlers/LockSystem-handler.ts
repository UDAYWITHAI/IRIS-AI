// The schema you inject into your Gemini tools array
export const lockSystemSchema = {
  name: 'lock_system_vault',
  description:
    "Instantly locks the IRIS OS system, disconnects the AI, and returns the user to the secure biometric lock screen. Use this strictly when the user says 'Lock the system', 'Lock down', or 'Activate Sentry Mode'."
}

// The execution payload
export const executeLockSystem = async () => {
  console.log('🔒 Executing Tactical Lockdown...')

  // @ts-ignore
  if (window.electron?.ipcRenderer) {
    // @ts-ignore
    window.electron.ipcRenderer.send('trigger-lockdown')
  } else {
    window.location.reload()
  }

  return 'System successfully locked. Rebooting secure interface...'
}
