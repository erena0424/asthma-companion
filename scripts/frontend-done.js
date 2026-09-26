const { execSync } = require("child_process");

const msg = process.argv[2];

if (!msg) {
  console.error("Error: You must provide a commit message.");
  process.exit(1);
}

function run(cmd) {
  console.log(`\n> ${cmd}`);
  execSync(cmd, { stdio: "inherit" });
}

console.log("Building frontend (production mode)...");
run("npm run build");

console.log("Pushing docs/ to gh-pages...");
run("git subtree push --prefix asthma-app/frontend/docs origin gh-pages");

console.log("Committing to current branch...");
run("git add .");
run(`git commit -m "${msg}"`);
run("git push");

console.log("Done.");