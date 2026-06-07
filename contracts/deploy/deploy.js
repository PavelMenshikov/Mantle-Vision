const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);
  console.log("Balance:", hre.ethers.formatEther(await hre.ethers.provider.getBalance(deployer.address)), "MNT");

  // Step 1: Deploy AgentIdentity
  const AgentIdentity = await hre.ethers.getContractFactory("AgentIdentity");
  const agentIdentity = await AgentIdentity.deploy();
  await agentIdentity.waitForDeployment();
  const agentIdentityAddr = await agentIdentity.getAddress();
  console.log("AgentIdentity deployed to:", agentIdentityAddr);

  // Step 2: Deploy SignalRecorder
  const SignalRecorder = await hre.ethers.getContractFactory("SignalRecorder");
  const signalRecorder = await SignalRecorder.deploy(agentIdentityAddr);
  await signalRecorder.waitForDeployment();
  const signalRecorderAddr = await signalRecorder.getAddress();
  console.log("SignalRecorder deployed to:", signalRecorderAddr);

  // Step 3: Link SignalRecorder to AgentIdentity
  const tx = await agentIdentity.setSignalRecorder(signalRecorderAddr);
  await tx.wait();
  console.log("SignalRecorder linked to AgentIdentity (setSignalRecorder)");

  // Step 4: Register an agent
  const agentURI = "https://mantle-vision.ai/agent.json";
  const registerTx = await agentIdentity.register(agentURI);
  const receipt = await registerTx.wait();
  const agentId = receipt.logs[0].topics[3]; // ERC-721 Transfer event -> tokenId
  console.log("Agent registered with ID:", hre.ethers.toBigInt(agentId).toString());

  // Output summary
  console.log("\n=== Deployment Summary ===");
  console.log(`AGENT_CONTRACT_ADDRESS=${agentIdentityAddr}`);
  console.log(`SignalRecorder: ${signalRecorderAddr}`);
  console.log(`Agent ID: ${hre.ethers.toBigInt(agentId).toString()}`);
  console.log("\nAdd AGENT_CONTRACT_ADDRESS to your .env file");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
