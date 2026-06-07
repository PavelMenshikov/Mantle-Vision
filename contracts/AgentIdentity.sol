// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title AgentIdentity
/// @notice ERC-8004 compatible agent identity registry.
///         Each agent is an NFT with on-chain metadata, signal counter, and accuracy.
contract AgentIdentity is ERC721URIStorage, Ownable {

    uint256 private _nextTokenId;
    address private _signalRecorder;

    struct AccuracyMetrics {
        uint256 totalSignals;
        uint256 accurateSignals;
    }

    mapping(uint256 => AccuracyMetrics) private _accuracy;
    mapping(uint256 => mapping(string => bytes)) private _metadata;

    event Registered(uint256 indexed agentId, string agentURI, address indexed owner);
    event URIUpdated(uint256 indexed agentId, string newURI, address indexed updatedBy);
    event MetadataSet(uint256 indexed agentId, string indexed metadataKey, bytes metadataValue);
    event AccuracyUpdated(uint256 indexed agentId, uint256 totalSignals, uint256 accurateSignals);

    constructor() ERC721("Mantle Vision Agent", "MVA") Ownable(msg.sender) {}

    modifier onlySignalRecorder() {
        require(_signalRecorder != address(0) && msg.sender == _signalRecorder, "AgentIdentity: not signal recorder");
        _;
    }

    function setSignalRecorder(address recorder) external onlyOwner {
        _signalRecorder = recorder;
    }

    function getSignalRecorder() external view returns (address) {
        return _signalRecorder;
    }

    function register(string calldata agentURI) external returns (uint256 agentId) {
        agentId = _nextTokenId++;
        _safeMint(msg.sender, agentId);
        _setTokenURI(agentId, agentURI);
        emit Registered(agentId, agentURI, msg.sender);
    }

    function setAgentURI(uint256 agentId, string calldata newURI) external {
        require(_isAuthorized(ownerOf(agentId), msg.sender, agentId), "AgentIdentity: not owner or approved");
        _setTokenURI(agentId, newURI);
        emit URIUpdated(agentId, newURI, msg.sender);
    }

    function getMetadata(uint256 agentId, string memory metadataKey) external view returns (bytes memory) {
        return _metadata[agentId][metadataKey];
    }

    function setMetadata(uint256 agentId, string memory metadataKey, bytes memory metadataValue) external {
        require(_isAuthorized(ownerOf(agentId), msg.sender, agentId), "AgentIdentity: not owner or approved");
        _metadata[agentId][metadataKey] = metadataValue;
        emit MetadataSet(agentId, metadataKey, metadataValue);
    }

    function recordSignal(uint256 agentId) external onlySignalRecorder {
        _accuracy[agentId].totalSignals++;
    }

    function reportAccurate(uint256 agentId) external onlySignalRecorder {
        _accuracy[agentId].accurateSignals++;
    }

    function getSignalCount(uint256 agentId) external view returns (uint256 totalSignals) {
        return _accuracy[agentId].totalSignals;
    }

    function getAccuracy(uint256 agentId) external view returns (
        uint256 totalSignals,
        uint256 accurateSignals,
        uint256 accuracyBasisPoints
    ) {
        AccuracyMetrics memory m = _accuracy[agentId];
        totalSignals = m.totalSignals;
        accurateSignals = m.accurateSignals;
        accuracyBasisPoints = m.totalSignals > 0
            ? (m.accurateSignals * 10_000) / m.totalSignals
            : 0;
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721URIStorage) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    function tokenURI(uint256 tokenId) public view override(ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }
}
