#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// ── helpers ──────────────────────────────────────────────────────────────────

function getGlobalNodeModules() {
    // Returns the global node_modules path e.g. C:\Users\kt48712\AppData\Roaming\npm\node_modules
    return execSync("npm root -g").toString().trim();
}

function ensureArchiver() {
    const globalModules = getGlobalNodeModules();
    const archiverPath = path.join(globalModules, "archiver");

    if (!fs.existsSync(archiverPath)) {
        console.log('📦 Installing "archiver" globally...');
        execSync("npm install -g archiver", { stdio: "inherit" });
    }

    // Require directly from the global path since require() doesn't scan global node_modules
    return require(archiverPath);
}

function isExcludedFolder(name) {
    // Exclude dot-folders EXCEPT .github, plus node_modules and __pycache__
    if (name === "node_modules" || name === "__pycache__") return true;
    if (name.startsWith(".") && name !== ".github") return true;
    return false;
}

function copyDirRecursive(src, dest) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
        if (isExcludedFolder(entry.name)) continue; // skip unwanted folders/files
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);
        if (entry.isDirectory()) {
            copyDirRecursive(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

function deleteDirRecursive(dirPath) {
    fs.rmSync(dirPath, { recursive: true, force: true });
}

// ── main ─────────────────────────────────────────────────────────────────────

async function main() {
    // Install globally if needed, and require from the global path directly
    const archiver = ensureArchiver();

    // 1. Resolve input folder (default: cwd)
    const inputFolder = path.resolve(process.argv[2] || process.cwd());

    if (!fs.existsSync(inputFolder)) {
        console.error(`❌  Folder not found: ${inputFolder}`);
        process.exit(1);
    }

    console.log(`📂 Source folder : ${inputFolder}`);

    // Collect top-level directories only
    const entries = fs.readdirSync(inputFolder, { withFileTypes: true });
    const topLevelDirs = entries.filter(
        (e) => e.isDirectory() && !isExcludedFolder(e.name)
    );

    if (topLevelDirs.length === 0) {
        console.log("⚠️  No eligible folders found. Nothing to do.");
        process.exit(0);
    }

    // Staging area lives inside the input folder so the zip ends up there cleanly
    const stagingRoot = path.join(inputFolder, `__zip_staging_${Date.now()}__`);
    fs.mkdirSync(stagingRoot);

    // 2 & 3. Copy each top-level folder into staging (stripping excluded paths)
    console.log(`\n🗂️  Copying ${topLevelDirs.length} folder(s) to staging...`);
    for (const dir of topLevelDirs) {
        const src = path.join(inputFolder, dir.name);
        const dest = path.join(stagingRoot, dir.name);
        console.log(`   • ${dir.name}`);
        copyDirRecursive(src, dest);
    }

    // 4 & 5. Zip the staging folder into the input folder
    const timestamp = new Date()
        .toISOString()
        .replace(/[:.]/g, "-")
        .replace("T", "_")
        .slice(0, 19);
    const zipName = `archive_${timestamp}.zip`;
    const zipPath = path.join(inputFolder, zipName);

    console.log(`\n🤐 Creating zip: ${zipName}`);

    await new Promise((resolve, reject) => {
        const output = fs.createWriteStream(zipPath);
        const archive = archiver("zip", { zlib: { level: 9 } });

        output.on("close", resolve);
        archive.on("error", reject);

        archive.pipe(output);
        // Add staging contents; folder names at the root of the zip
        archive.directory(stagingRoot, false);
        archive.finalize();
    });

    const sizeMB = (fs.statSync(zipPath).size / 1024 / 1024).toFixed(2);
    console.log(`   ✅ Saved (${sizeMB} MB) → ${zipPath}`);

    // 6. Delete staging copies
    console.log("\n🧹 Cleaning up staging folder...");
    deleteDirRecursive(stagingRoot);

    console.log("\n🎉 Done!");
}

main().catch((err) => {
    console.error("❌ Unexpected error:", err.message);
    process.exit(1);
});