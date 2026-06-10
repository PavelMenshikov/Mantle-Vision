// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "./AgentIdentity.sol";

/// @title SignalRecorder
/// @notice Records AI agent signals on-chain linked to AgentIdentity.
contract SignalRecorder {

    enum SignalType { WHALE_ALERT, DEX_ANOMALY, MARKET_TREND, GAS_SPIKE, AI_PREDICTION }
    enum Direction { BULLISH, BEARISH, NEUTRAL }
    enum Confidence { HIGH, MEDIUM, LOW }

    struct Signal {
        uint256 id;
        uint256 agentId;
        SignalType signalType;
        string asset;
        Direction direction;
        Confidence confidence;
        string reasoning;
        bytes32 txHash;
        uint256 timestamp;
        address recorder;
    }

    AgentIdentity public immutable agentIdentity;
    Signal[] private _signals;
    mapping(uint256 => uint256[]) private _agentSignals;

    event SignalRecorded(
        uint256 indexed id,
        uint256 indexed agentId,
        SignalType signalType,
        string asset,
        Direction direction,
        Confidence confidence,
        string reasoning,
        bytes32 txHash,
        uint256 timestamp,
        address indexed recorder
    );

    constructor(address agentIdentity_) {
        require(agentIdentity_ != address(0), "SignalRecorder: invalid identity address");
        agentIdentity = AgentIdentity(agentIdentity_);
    }

    modifier onlyAgentOwner(uint256 agentId) {
        require(agentIdentity.ownerOf(agentId) == msg.sender, "SignalRecorder: caller is not agent owner");
        _;
    }

    function recordSignal(
        uint256 agentId,
        SignalType signalType,
        string calldata asset,
        Direction direction,
        Confidence confidence,
        string calldata reasoning,
        bytes32 txHash
    ) external onlyAgentOwner(agentId) returns (uint256 id) {
        id = _signals.length;
        _signals.push(Signal({
            id: id,
            agentId: agentId,
            signalType: signalType,
            asset: asset,
            direction: direction,
            confidence: confidence,
            reasoning: reasoning,
            txHash: txHash,
            timestamp: block.timestamp,
            recorder: msg.sender
        }));
        _agentSignals[agentId].push(id);
        agentIdentity.recordSignal(agentId);
        emit SignalRecorded(id, agentId, signalType, asset, direction, confidence, reasoning, txHash, block.timestamp, msg.sender);
    }

    function getSignalCount() external view returns (uint256) {
        return _signals.length;
    }

    function getSignal(uint256 id) external view returns (Signal memory) {
        require(id < _signals.length, "SignalRecorder: signal does not exist");
        return _signals[id];
    }

    function getRecentSignals(uint256 count) external view returns (Signal[] memory) {
        uint256 total = _signals.length;
        uint256 resultCount = count < total ? count : total;
        Signal[] memory result = new Signal[](resultCount);
        for (uint256 i = 0; i < resultCount; i++) {
            result[i] = _signals[total - resultCount + i];
        }
        return result;
    }

    function getSignalsPagination(uint256 offset, uint256 limit) external view returns (Signal[] memory) {
        uint256 total = _signals.length;
        if (offset >= total) return new Signal[](0);
        uint256 resultCount = limit;
        if (offset + resultCount > total) resultCount = total - offset;
        Signal[] memory result = new Signal[](resultCount);
        for (uint256 i = 0; i < resultCount; i++) {
            result[i] = _signals[offset + i];
        }
        return result;
    }

    function getSignalsByAgent(uint256 agentId, uint256 offset, uint256 limit)
        external view returns (Signal[] memory)
    {
        uint256[] storage agentIds = _agentSignals[agentId];
        uint256 total = agentIds.length;
        if (offset >= total) return new Signal[](0);
        uint256 resultCount = limit;
        if (offset + resultCount > total) resultCount = total - offset;
        Signal[] memory result = new Signal[](resultCount);
        for (uint256 i = 0; i < resultCount; i++) {
            result[i] = _signals[agentIds[offset + i]];
        }
        return result;
    }

    function getAgentSignalCount(uint256 agentId) external view returns (uint256) {
        return _agentSignals[agentId].length;
    }
}
