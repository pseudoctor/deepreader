import { execFileSync } from "node:child_process";

function has(name) {
  return Boolean(process.env[name]?.trim());
}

function namesPresent(names) {
  return names.every(has);
}

function maskedStatus(names) {
  return names.map((name) => `${name}=${has(name) ? "set" : "missing"}`).join(", ");
}

function findDeveloperIdIdentity() {
  if (process.platform !== "darwin") {
    return null;
  }

  try {
    const output = execFileSync("security", ["find-identity", "-v", "-p", "codesigning"], {
      encoding: "utf8",
    });
    return output
      .split("\n")
      .find((line) => line.includes("Developer ID Application:"))?.trim() ?? null;
  } catch {
    return null;
  }
}

const notarizationOptions = [
  {
    label: "App Store Connect API key",
    names: ["APPLE_API_KEY", "APPLE_API_KEY_ID", "APPLE_API_ISSUER"],
  },
  {
    label: "Apple ID app-specific password",
    names: ["APPLE_ID", "APPLE_APP_SPECIFIC_PASSWORD", "APPLE_TEAM_ID"],
  },
  {
    label: "notarytool keychain profile",
    names: ["APPLE_KEYCHAIN_PROFILE"],
    optionalNames: ["APPLE_KEYCHAIN"],
  },
];

const signingOptions = [
  {
    label: "certificate link",
    names: ["CSC_LINK"],
    optionalNames: ["CSC_KEY_PASSWORD"],
  },
  {
    label: "keychain identity name",
    names: ["CSC_NAME"],
  },
];

const notarization = notarizationOptions.find((option) => namesPresent(option.names));
const signing = signingOptions.find((option) => namesPresent(option.names));
const localIdentity = findDeveloperIdIdentity();

console.log("Deep Reading macOS signing environment check");
console.log("");

if (signing) {
  console.log(`Signing: OK via ${signing.label}`);
  console.log(`  ${maskedStatus([...signing.names, ...(signing.optionalNames ?? [])])}`);
} else if (localIdentity) {
  console.log("Signing: OK via local Developer ID Application identity");
  console.log(`  ${localIdentity.replace(/^\s*\d+\)\s*/, "")}`);
} else {
  console.log("Signing: missing");
  console.log("  Provide CSC_LINK or CSC_NAME, or install a Developer ID Application certificate.");
}

console.log("");

if (notarization) {
  console.log(`Notarization: OK via ${notarization.label}`);
  console.log(`  ${maskedStatus([...notarization.names, ...(notarization.optionalNames ?? [])])}`);
} else {
  console.log("Notarization: missing");
  console.log("  Provide one of:");
  for (const option of notarizationOptions) {
    console.log(`  - ${option.names.join(", ")}`);
  }
}

if ((signing || localIdentity) && notarization) {
  process.exit(0);
}

process.exit(1);
