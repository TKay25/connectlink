import re

with open('hr_dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find from '<!-- ===== DASHBOARD GRID ===== -->' to next module
start_marker = '<!-- ===== DASHBOARD GRID ===== -->'
end_marker = '<!-- ===== MODULE: EMPLOYEES ===== -->'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

print(f"start_idx={start_idx}, end_idx={end_idx}")
print(f"Content before start: {repr(content[start_idx-5:start_idx+5])}")
print(f"Content at end: {repr(content[end_idx-5:end_idx+5])}")

if start_idx == -1 or end_idx == -1:
    print('Markers not found')
    exit()

new_content = '''            <!-- ===== DASHBOARD GRID (Redesigned) ===== -->
            <div class="dash-grid">
                <div class="dash-kpi">
                    <div class="hr-stat-card" style="border-left:3px solid #2563eb;"><div style="display:flex;align-items:center;gap:8px;"><div style="width:32px;height:32px;border-radius:8px;background:#e8f0fe;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;"><i class="bi bi-people-fill"></i></div><div><div style="font-size:0.5rem;color:var(--text-muted);text-transform:uppercase;">Total Employees</div><div style="font-size:1rem;font-weight:800;color:var(--text-primary);" id="statTotalEmployees">0</div></div></div></div>
                    <div class="hr-stat-card" style="border-left:3px solid #d97706;"><div style="display:flex;align-items:center;gap:8px;"><div style="width:32px;height:32px;border-radius:8px;background:#fff3e0;display:flex;align-items:center;justify-content:center;color:#d97706;flex-shrink:0;"><i class="bi bi-calendar-check"></i></div><div><div style="font-size:0.5rem;color:var(--text-muted);text-transform:uppercase;">On Leave Today</div><div style="font-size:1rem;font-weight:800;color:var(--text-primary);" id="statOnLeave">0</div></div></div></div>
                    <div class="hr-stat-card" style="border-left:3px solid #7c3aed;"><div style="display:flex;align-items:center;gap:8px;"><div style="width:32px;height:32px;border-radius:8px;background:#f5f0ff;display:flex;align-items:center;justify-content:center;color:#7c3aed;flex-shrink:0;"><i class="bi bi-wallet2"></i></div><div><div style="font-size:0.5rem;color:var(--text-muted);text-transform:uppercase;">Payroll (Month)</div><div style="font-size:1rem;font-weight:800;color:var(--text-primary);" id="statPayroll">$0</div></div></div></div>
                    <div class="hr-stat-card" style="border-left:3px solid #dc2626;"><div style="display:flex;align-items:center;gap:8px;"><div style="width:32px;height:32px;border-radius:8px;background:#fce4ec;display:flex;align-items:center;justify-content:center;color:#dc2626;flex-shrink:0;"><i class="bi bi-exclamation-triangle"></i></div><div><div style="font-size:0.5rem;color:var(--text-muted);text-transform:uppercase;">Pending Requests</div><div style="font-size:1rem;font-weight:800;color:var(--text-primary);" id="statPendingRequests">0</div></div></div></div>
                </div>
                <div class="dash-cols">
                    <div class="dash-col"><div class="dash-col-header"><i class="bi bi-people-fill" style="color:#2563eb;"></i> Human Resources</div>
                        <div class="hr-stat-card" style="padding:6px 10px;"><div style="font-size:0.5rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:3px;">Departments</div><div id="deptBreakdown" style="font-size:0.55rem;color:var(--text-secondary);"><span style="color:#9ca3af;">Loading...</span></div></div>
                        <div class="hr-stat-card" style="padding:6px 10px;"><div style="font-size:0.5rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:3px;">Employee Status</div><div style="display:flex;gap:6px;flex-wrap:wrap;"><span style="font-size:0.55rem;color:#16a34a;"><span style="font-weight:700;" id="statActiveEmployees">0</span> Active</span><span style="font-size:0.55rem;color:#dc2626;"><span style="font-weight:700;" id="statInactiveEmployees">0</span> Inactive</span><span style="font-size:0.55rem;color:#d97706;"><span style="font-weight:700;" id="statOnLeaveEmployees">0</span> On Leave</span></div></div>
                        <div class="hr-stat-card" onclick="showModule('employees')" style="cursor:pointer;margin-top:auto;"><div style="display:flex;align-items:center;gap:8px;padding:4px 0;"><i class="bi bi-person-plus" style="color:#2563eb;"></i><span style="font-size:0.6rem;font-weight:600;">Manage Employees →</span></div></div>
                    </div>
                    <div class="dash-col"><div class="dash-col-header"><i class="bi bi-calendar-check" style="color:#d97706;"></i> Leave &amp; Activity</div>
                        <div class="hr-stat-card" style="padding:6px 10px;"><div style="font-size:0.5rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:3px;">This Month</div><div style="display:flex;gap:8px;flex-wrap:wrap;"><span style="font-size:0.55rem;color:var(--text-secondary);"><span style="font-weight:700;" id="statApprovedLeaves">0</span> Approved</span><span style="font-size:0.55rem;color:var(--text-secondary);"><span style="font-weight:700;" id="statTotalDays">0</span> Days taken</span></div></div>
                        <div class="hr-stat-card" style="padding:6px 10px;"><div style="font-size:0.5rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:3px;">Leave Types</div><div style="display:flex;gap:6px;flex-wrap:wrap;"><span style="font-size:0.55rem;color:#2563eb;"><span style="font-weight:700;" id="statAnnualLeave">0</span> Annual</span><span style="font-size:0.55rem;color:#7c3aed;"><span style="font-weight:700;" id="statSickLeave">0</span> Sick</span><span style="font-size:0.55rem;color:#0891b2;"><span style="font-weight:700;" id="statOtherLeave">0</span> Other</span></div></div>
                        <div class="hr-stat-card" onclick="showModule('leave')" style="cursor:pointer;"><div style="display:flex;align-items:center;gap:8px;padding:4px 0;"><i class="bi bi-send-plus" style="color:#16a34a;"></i><span style="font-size:0.6rem;font-weight:600;">New Leave Request →</span></div></div>
                        <div class="dash-fill" style="flex:1;min-height:0;"><div class="hr-card" style="flex:1;"><div class="card-header-custom" style="padding:4px 8px;"><span style="font-size:0.5rem;font-weight:600;"><i class="bi bi-clock-history"></i> Recent Activity</span></div><div class="card-body-custom" style="padding:0;"><div id="activityTimeline" style="padding:8px;text-align:center;color:var(--text-muted);font-size:0.5rem;"><i class="bi bi-inbox" style="font-size:0.8rem;display:block;margin-bottom:2px;"></i> No recent activity.</div></div></div></div>
                    </div>
                    <div class="dash-col"><div class="dash-col-header"><i class="bi bi-briefcase-fill" style="color:#7c3aed;"></i> Finance &amp; Assets</div>
                        <div class="hr-stat-card" style="padding:6px 10px;"><div style="font-size:0.5rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:3px;">PAYE Tax Table</div><div id="payeDashboardStatus" style="font-size:0.55rem;color:var(--text-secondary);"><span style="color:#9ca3af;">Loading...</span></div></div>
                        <div class="hr-stat-card" style="padding:6px 10px;"><div style="font-size:0.5rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:3px;">Asset Summary</div><div id="assetSummary" style="font-size:0.55rem;color:var(--text-secondary);"><span style="color:#9ca3af;">Loading...</span></div></div>
                        <div class="hr-stat-card" style="padding:6px 10px;"><div style="font-size:0.5rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:3px;">Department Budget</div><div style="display:flex;gap:6px;flex-wrap:wrap;"><span style="font-size:0.55rem;color:var(--text-secondary);"><span style="font-weight:700;" id="statDeptBudget">$0</span> Allocated</span><span style="font-size:0.55rem;color:#16a34a;"><span style="font-weight:700;" id="statDeptSpent">$0</span> Spent</span></div></div>
                        <div class="hr-stat-card" onclick="showModule('payroll')" style="cursor:pointer;"><div style="display:flex;align-items:center;gap:8px;padding:4px 0;"><i class="bi bi-wallet2" style="color:#7c3aed;"></i><span style="font-size:0.6rem;font-weight:600;">Open Payroll →</span></div></div>
                        <div class="hr-stat-card" onclick="showModule('assets')" style="cursor:pointer;"><div style="display:flex;align-items:center;gap:8px;padding:4px 0;"><i class="bi bi-boxes" style="color:#0891b2;"></i><span style="font-size:0.6rem;font-weight:600;">Asset Register →</span></div></div>
                    </div>
                </div>
            </div>

        </div>

        <!-- ===== MODULE: EMPLOYEES ===== -->'

result = content[:start_idx] + new_content + content[end_idx:]

with open('hr_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(result)

print(f'Success! Replaced {end_idx - start_idx} chars with {len(new_content)} chars.')
