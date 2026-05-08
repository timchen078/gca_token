// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title GCA fixed-supply ERC-20 token
/// @notice Deploys 1,000,000,000 GCA to the deployer. No minting, burning, taxes, blacklist, or admin controls.
contract GCAToken {
    string public constant name = "GCA";
    string public constant symbol = "GCA";
    uint8 public constant decimals = 18;

    uint256 public constant totalSupply = 1_000_000_000 * 10 ** uint256(decimals);

    mapping(address account => uint256 balance) private _balances;
    mapping(address owner => mapping(address spender => uint256 amount)) private _allowances;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    error InvalidAddress();
    error InsufficientBalance();
    error InsufficientAllowance();

    constructor() {
        _balances[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }

    function balanceOf(address account) external view returns (uint256) {
        return _balances[account];
    }

    function allowance(address owner, address spender) external view returns (uint256) {
        return _allowances[owner][spender];
    }

    function transfer(address to, uint256 value) external returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }

    function approve(address spender, uint256 value) external returns (bool) {
        if (spender == address(0)) revert InvalidAddress();

        _allowances[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        uint256 currentAllowance = _allowances[from][msg.sender];
        if (currentAllowance < value) revert InsufficientAllowance();

        unchecked {
            _allowances[from][msg.sender] = currentAllowance - value;
        }
        emit Approval(from, msg.sender, _allowances[from][msg.sender]);

        _transfer(from, to, value);
        return true;
    }

    function _transfer(address from, address to, uint256 value) private {
        if (to == address(0)) revert InvalidAddress();

        uint256 fromBalance = _balances[from];
        if (fromBalance < value) revert InsufficientBalance();

        unchecked {
            _balances[from] = fromBalance - value;
            _balances[to] += value;
        }

        emit Transfer(from, to, value);
    }
}
