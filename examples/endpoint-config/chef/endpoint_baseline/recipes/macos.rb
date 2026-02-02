# endpoint_baseline::macos
# Minimal baseline enforcement (illustrative, not exhaustive)

# Enable macOS Application Firewall
execute 'enable_firewall' do
  command '/usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on'
  not_if  "/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | grep -qi 'enabled'"
end

# Require screen lock in 10 minutes (example)
execute 'set_screensaver_timeout' do
  command "defaults -currentHost write com.apple.screensaver idleTime -int 600"
  not_if  "defaults -currentHost read com.apple.screensaver idleTime 2>/dev/null | grep -q '^600$'"
end

# Gate-like check: fail converge if FileVault not enabled (useful for ring gating)
ruby_block 'filevault_must_be_on' do
  block do
    status = `fdesetup status`.downcase
    unless status.include?('filevault is on')
      raise "FileVault is not enabled; block rollout/promotion"
    end
  end
end
