# Security Policy for macOS-MCP

## ⚠️ Critical Security Notice

**macOS-MCP is NOT sandboxed.** Every tool call executes real actions directly on your macOS system with no intermediate layer, simulation, or preview mode. Understand the risks before deployment.

## Understanding the Risks

### Full System Access
macOS-MCP operates with Accessibility API permissions, enabling:
- File system operations (create, read, modify, delete)
- Application launching and control
- Keyboard and mouse input simulation
- System preference modifications
- Shell command execution with user privileges

### Irreversible Operations
Many operations cannot be undone:
- File deletions are permanent
- Data overwrites cannot be recovered
- System modifications may persist
- No undo functionality available

### No Safety Preview
Unlike traditional automation tools, macOS-MCP:
- Cannot preview actions before execution
- Does not simulate operations
- Executes immediately upon LLM decision
- Provides no confirmation dialogs

## ❌ Where NOT to Deploy

**Do NOT deploy macOS-MCP on:**

- **Production servers or workstations** - Real business systems
- **Systems with irreplaceable data** - Photos, documents, financial records
- **Compliance-regulated environments** - Healthcare (HIPAA), finance (PCI), government systems
- **Shared multi-user systems** - Systems accessed by multiple users
- **Any machine you cannot afford to lose** - Critical infrastructure

## ✅ Recommended Safe Deployment Environments

### Virtual Machines
- **Snapshots**: Create snapshots before each session for rollback
- **Isolation**: Use separate VMs for testing and production
- **Resources**: Allocate minimal resources to limit blast radius

### Windows Sandbox (Windows hosts)
- Isolated environment built into Windows 10/11 Pro
- Automatic cleanup after use
- No persistent changes to host system

### Dedicated Test Systems
- Machines with no production data
- Isolated network segments
- Regular backups maintained
- Fresh OS installation or snapshots between tests

### Isolated Network Environments
- Air-gapped systems
- No internet connectivity
- Limited access to sensitive resources
- Monitored and logged environments

## Tool Risk Classification

### 🔴 High-Risk Tools
These tools can perform permanent system modifications:

| Tool | Capabilities | Risks |
|------|-------------|-------|
| `Shell` | Execute arbitrary commands | Full system access, irreversible changes |
| `Click` | Interact with UI elements | Can trigger destructive actions |
| `Type` | Input text to applications | May delete or overwrite data |
| `Drag` | Move/drag UI elements | Can relocate or delete items |
| `Shortcut` | Press keyboard shortcuts | Cmd+Q quits apps, Cmd+Delete deletes items |

### 🟡 Medium-Risk Tools
These tools can modify state but with some reversibility:

| Tool | Capabilities | Risks |
|------|-------------|-------|
| `App` | Launch/close applications | Can start unwanted processes |
| `Scroll` | Navigate UI content | May trigger unintended actions |
| `Move` | Move mouse cursor | Could trigger hover-based effects |

### 🟢 Low-Risk Tools
These tools only read information:

| Tool | Capabilities | Risks |
|------|-------------|-------|
| `Snapshot` | Capture desktop state | No system modifications |
| `Wait` | Pause execution | No system impact |
| `Scrape` | Extract webpage content | Read-only operation |

## Best Practices

### 1. Run with Least Privilege
- Use unprivileged user accounts for testing
- Avoid running with sudo/admin privileges
- Limit Accessibility permissions to necessary applications

### 2. Monitor Tool Usage
- Log all operations performed
- Review AI-generated action plans before execution
- Monitor system changes in real-time
- Implement approval workflows for critical operations

### 3. Maintain Regular Backups
- Full system backups before each session
- Incremental backups between major changes
- Test backup restoration procedures
- Keep backups isolated from production systems

### 4. Use Network Isolation
- Deploy on isolated network segments
- Disable internet access if not needed
- Use firewall rules to restrict outbound connections
- Monitor network activity

### 5. Test in Safe Environments First
- Always test workflows in VMs or sandboxes
- Start with non-critical operations
- Gradually increase complexity and scope
- Verify behavior matches expectations

### 6. Implement Access Controls
- Restrict Accessibility permissions to trusted apps only
- Use separate user accounts for different purposes
- Implement approval processes for high-risk operations
- Audit access logs regularly

### 7. Document and Review Operations
- Keep detailed logs of all operations
- Review AI decision-making processes
- Document lessons learned
- Build organizational knowledge

## Accessibility Permissions

macOS-MCP requires Accessibility permissions to function. This is a system-level privilege that should be granted carefully.

### Granting Permissions Safely

1. **System Settings** > **Privacy & Security** > **Accessibility**
2. Click the lock icon and authenticate
3. **Only add trusted applications** (Terminal, VS Code, etc.)
4. Remove permissions for applications that no longer need them
5. Regularly audit the permission list

### Revoking Permissions

To revoke Accessibility permissions:
1. **System Settings** > **Privacy & Security** > **Accessibility**
2. Click the lock icon
3. Select the application and click the **-** button
4. Permissions are revoked immediately

## Vulnerability Reporting

### Responsible Disclosure

If you discover a security vulnerability in macOS-MCP:

1. **Do NOT** disclose the vulnerability publicly
2. **Do NOT** create a public GitHub issue
3. **Email** security concerns to: jeogeoalukka@gmail.com
4. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fixes (if any)
5. Allow reasonable time for remediation before public disclosure

### Vulnerability Response Timeline

- **Initial response**: Within 48 hours
- **Assessment**: Within 1 week
- **Fix development**: As quickly as possible
- **Release**: Prioritized security updates
- **Disclosure**: After fix is released

## Telemetry and Data Collection

### Current Status
macOS-MCP does **not currently collect any telemetry data**.

### Privacy Protection
- No operation tracking
- No argument or output logging (except locally)
- No personal data collection
- No external reporting

## Compliance Considerations

### Regulatory Environments

macOS-MCP is **NOT suitable** for:
- **HIPAA** (healthcare data)
- **PCI-DSS** (payment card data)
- **SOC 2** (audit-required systems)
- **GDPR** (sensitive personal data)
- **FedRAMP** (government systems)

Consider compliance implications before use.

## Security Updates

Stay informed about security updates:

1. Watch the GitHub repository
2. Subscribe to release notifications
3. Review changelog for security fixes
4. Update promptly when patches are released

## Additional Resources

### Related Documentation
- See [CLAUDE.md](CLAUDE.md) for architecture details
- See [README.md](README.md) for usage information
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines

### External Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [macOS Security](https://support.apple.com/en-us/HT201222)

## License

macOS-MCP is licensed under the MIT License. Security policy updates may occur independently of version releases.

---

**Last Updated**: April 2026

For questions about security, contact: jeogeoalukka@gmail.com
