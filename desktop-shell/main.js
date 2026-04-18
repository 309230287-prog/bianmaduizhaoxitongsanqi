const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

const PORT = Number(process.env.PRODUCT_MATCHER_PORT || 18765);
const HOST = '127.0.0.1';
const SERVER_URL = `http://${HOST}:${PORT}`;

let mainWindow = null;
let backendProcess = null;

function resolveRepoRoot() {
  return path.resolve(__dirname, '..');
}

function resolveDevPython() {
  return process.env.PRODUCT_MATCHER_PYTHON || '';
}

function resolveDevServerEntry() {
  return path.join(resolveRepoRoot(), 'src', 'product_matcher', 'desktop_server.py');
}

function resolvePackagedServer() {
  return path.join(process.resourcesPath, 'backend', 'product-matcher-server.exe');
}

function startBackend() {
  if (app.isPackaged) {
    const serverExe = resolvePackagedServer();
    backendProcess = spawn(serverExe, ['--host', HOST, '--port', String(PORT)], {
      cwd: path.dirname(serverExe),
      stdio: 'ignore',
      windowsHide: true,
    });
    return;
  }

  const pythonExe = resolveDevPython();
  if (!pythonExe) {
    throw new Error('缺少 PRODUCT_MATCHER_PYTHON 环境变量，无法启动桌面客户端开发模式。');
  }

  const repoRoot = resolveRepoRoot();
  backendProcess = spawn(
    pythonExe,
    [resolveDevServerEntry(), '--host', HOST, '--port', String(PORT)],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONPATH: path.join(repoRoot, 'src'),
      },
      stdio: 'ignore',
      windowsHide: true,
    }
  );
}

async function waitForServer(retries = 60) {
  for (let index = 0; index < retries; index += 1) {
    try {
      const response = await fetch(`${SERVER_URL}/health`);
      if (response.ok) {
        return;
      }
    } catch (error) {
      // server still starting
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error('本地后端服务启动超时。');
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1180,
    minHeight: 760,
    autoHideMenuBar: true,
    backgroundColor: '#f5efe5',
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
    },
  });
  mainWindow.loadURL(SERVER_URL);
}

function stopBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
  backendProcess = null;
}

app.on('window-all-closed', () => {
  stopBackend();
  app.quit();
});

app.on('before-quit', () => {
  stopBackend();
});

app.whenReady().then(async () => {
  try {
    startBackend();
    await waitForServer();
    createWindow();
  } catch (error) {
    dialog.showErrorBox('客户端启动失败', String(error && error.message ? error.message : error));
    stopBackend();
    app.quit();
  }
});
