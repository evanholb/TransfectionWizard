/**
 * File operations using the File System Access API
 * Provides save dialog in supported browsers (Chrome, Edge, Opera)
 * Falls back to regular download for other browsers
 */

async function saveFileWithDialog(dataBase64, filename, mimeType) {
    // Convert base64 to blob
    const byteCharacters = atob(dataBase64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: mimeType });

    // Try File System Access API first (Chrome, Edge, Opera)
    if ('showSaveFilePicker' in window) {
        try {
            const fileExtension = filename.split('.').pop();
            const handle = await window.showSaveFilePicker({
                suggestedName: filename,
                types: [{
                    description: 'File',
                    accept: { [mimeType]: ['.' + fileExtension] }
                }]
            });
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
            return true;
        } catch (err) {
            if (err.name === 'AbortError') {
                // User cancelled, don't fall back to download
                return false;
            }
            // Fall through to regular download on other errors
        }
    }

    // Fallback: regular download for browsers that don't support File System Access API
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return true;
}
