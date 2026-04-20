// OptiMATE v1-light provider adapter
import { spawn } from "child_process";
import { writeFile, readFile, unlink } from "fs/promises";
import { join } from "path";
import { tmpdir } from "os";

export const id = "optimate";
export const label = "OptiMATE";

export const isAvailable = () => !!(process.env.OPTIMATE_DIR || process.env.OPTIMATE_PYTHON);

const RUN_TIMEOUT_MS = 900_000;

export async function runJob({ jobId, prompt, files, setJob }) {
  const optimateDir    = process.env.OPTIMATE_DIR;
  const optimatePython = process.env.OPTIMATE_PYTHON ?? "python3";
  const llmProvider    = process.env.OPTIMATE_LLM_PROVIDER ?? "openai";

  const tempFiles = [];
  console.log(`[OptiMATE] Starting job ${jobId} | python=${optimatePython} | dir=${optimateDir} | provider=${llmProvider}`);

  try {
    const promptFile = join(tmpdir(), `optimate_${jobId}.txt`);
    await writeFile(promptFile, prompt, "utf8");
    tempFiles.push(promptFile);

    const dataArgs = [];
    for (const file of files) {
      const tmpPath = join(tmpdir(), `optimate_${jobId}_${file.originalname}`);
      await writeFile(tmpPath, file.buffer);
      tempFiles.push(tmpPath);
      dataArgs.push("--data", tmpPath);
    }

    const args = [
      join(optimateDir, "cli.py"),
      "run",
      "--input", promptFile,
      ...dataArgs,
      "--provider", llmProvider,
    ];

    const output = await spawnAsync(optimatePython, args, {
      cwd: optimateDir,
      env: { ...process.env },
      timeoutMs: RUN_TIMEOUT_MS,
    });

    const match = output.stdout.match(/Done!\s+Report:\s+(\S+)/);
    if (!match) {
      throw new Error(`OptiMATE did not produce a report.\n\nCLI output:\n${output.stdout}\n${output.stderr}`);
    }

    const reportPath = match[1];
    console.log(`[OptiMATE] Job ${jobId} done — report: ${reportPath}`);
    const report = await readFile(reportPath, "utf8");
    await setJob(jobId, { status: "done", output: report });

  } catch (err) {
    const message = err instanceof Error ? err.message : "OptiMATE pipeline failed";
    console.error(`[OptiMATE] Job ${jobId} FAILED:`, message);
    await setJob(jobId, { status: "error", error: message });
  } finally {
    for (const f of tempFiles) {
      unlink(f).catch(() => {});
    }
  }
}

function spawnAsync(cmd, args, { cwd, env, timeoutMs }) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, { cwd, env });
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d) => { stdout += d.toString(); });
    proc.stderr.on("data", (d) => { stderr += d.toString(); });

    const timer = setTimeout(() => {
      proc.kill();
      reject(new Error(`OptiMATE timed out after ${timeoutMs / 1000}s`));
    }, timeoutMs);

    proc.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error(`OptiMATE exited with code ${code}.\n\nstdout:\n${stdout}\n\nstderr:\n${stderr}`));
      }
    });

    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}
