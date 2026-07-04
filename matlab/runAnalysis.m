projectRoot = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot, 'matlab', 'functions'));

% Write all exported time-series outputs to the project results folder.
resultsDir = fullfile(projectRoot, 'results');
if ~isfolder(resultsDir)
    mkdir(resultsDir);
end

activePowerFile = fullfile(projectRoot, 'data', 'abq_buildings_active_power.csv');
powerFactorFile = fullfile(projectRoot, 'data', 'abq_buildings_power_factor.csv');
masterFile = fullfile(projectRoot, 'dss', 'Master.dss');

activePower = readProfileTable(activePowerFile);
powerFactor = readProfileTable(powerFactorFile);
validateProfiles(activePower, powerFactor);

% Map the first seven CSV building profiles onto the seven modeled 3-phase load buses.
buildingNames = activePower.Properties.VariableNames(2:8);
loadGroups = [
    struct('bus', "con_8",  'loads', {{'load_8A',  'load_8B',  'load_8C'}},  'building', string(buildingNames{1}))
    struct('bus', "con_9",  'loads', {{'load_9A',  'load_9B',  'load_9C'}},  'building', string(buildingNames{2}))
    struct('bus', "con_11", 'loads', {{'load_11A', 'load_11B', 'load_11C'}}, 'building', string(buildingNames{3}))
    struct('bus', "con_12", 'loads', {{'load_12A', 'load_12B', 'load_12C'}}, 'building', string(buildingNames{4}))
    struct('bus', "con_13", 'loads', {{'load_13A', 'load_13B', 'load_13C'}}, 'building', string(buildingNames{5}))
    struct('bus', "con_14", 'loads', {{'load_14A', 'load_14B', 'load_14C'}}, 'building', string(buildingNames{6}))
    struct('bus', "con_15", 'loads', {{'load_15A', 'load_15B', 'load_15C'}}, 'building', string(buildingNames{7}))
];

[DSSObj, DSSText] = startDSS();
cleanupDSS = onCleanup(@() cleanupOpenDSS(DSSObj));
[DSSCircuit, DSSSolution] = compileDSS(DSSObj, DSSText, masterFile);

% Run a sequence of static snapshots, one solve per 30-minute row in the CSV files.
DSSText.Command = 'set mode=snapshot';
allBusNames = string(DSSCircuit.AllBusNames);
busPowerKW = zeros(height(activePower), numel(allBusNames));
busPowerKvar = zeros(height(activePower), numel(allBusNames));
systemPowerKW = zeros(height(activePower), 1);
systemPowerKvar = zeros(height(activePower), 1);
appliedLoadRows = zeros(height(activePower) * numel(loadGroups), 4);

for stepIdx = 1:height(activePower)
    for groupIdx = 1:numel(loadGroups)
        totalKW = activePower{stepIdx, groupIdx + 1};
        pf = powerFactor{stepIdx, groupIdx + 1};
        totalKvar = kwPfToKvar(totalKW, pf);

        % Each building profile is represented by three single-phase loads at the same bus.
        phaseKW = totalKW / numel(loadGroups(groupIdx).loads);
        phaseKvar = totalKvar / numel(loadGroups(groupIdx).loads);

        for loadIdx = 1:numel(loadGroups(groupIdx).loads)
            DSSText.Command = sprintf( ...
                'edit load.%s kW=%.12f kvar=%.12f', ...
                loadGroups(groupIdx).loads{loadIdx}, phaseKW, phaseKvar);
        end

        rowIdx = (stepIdx - 1) * numel(loadGroups) + groupIdx;
        appliedLoadRows(rowIdx, :) = [stepIdx, groupIdx, totalKW, totalKvar];
    end

    DSSSolution.Solve();
    if DSSSolution.Converged ~= 1
        error('OpenDSS did not converge at time step %d (%s).', ...
            stepIdx, string(activePower.Datetime(stepIdx)));
    end

    % Aggregate kW/kvar by bus from power-conversion elements after the solve.
    [busPRow, busQRow] = collectBusPcElementPowers(DSSCircuit, allBusNames);
    busPowerKW(stepIdx, :) = busPRow;
    busPowerKvar(stepIdx, :) = busQRow;

    % OpenDSS reports circuit total power with load convention opposite to exported demand.
    totalPower = DSSCircuit.TotalPower;
    systemPowerKW(stepIdx) = -totalPower(1);
    systemPowerKvar(stepIdx) = -totalPower(2);
end

busPowerTable = buildBusPowerTable(activePower.Datetime, allBusNames, busPowerKW, busPowerKvar);
systemPowerTable = table(activePower.Datetime, systemPowerKW, systemPowerKvar, ...
    'VariableNames', {'Datetime', 'TotalKW', 'TotalKvar'});

appliedLoadTable = buildAppliedLoadTable(activePower.Datetime, loadGroups, appliedLoadRows);

writetable(busPowerTable, fullfile(resultsDir, 'bus_power_timeseries.csv'));
writetable(systemPowerTable, fullfile(resultsDir, 'system_power_timeseries.csv'));
writetable(appliedLoadTable, fullfile(resultsDir, 'applied_load_profiles.csv'));

function tbl = readProfileTable(filePath)
% Read a profile CSV and convert its first column into MATLAB datetimes.
opts = detectImportOptions(filePath);
opts = setvartype(opts, 1, 'char');
tbl = readtable(filePath, opts);
tbl.Datetime = datetime(tbl{:, 1}, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
end

function validateProfiles(activePower, powerFactor)
% Fail early if the paired CSV inputs cannot be used step-by-step together.
if height(activePower) ~= height(powerFactor)
    error('Active power and power factor profiles must have the same number of rows.');
end

if width(activePower) < 8 || width(powerFactor) < 8
    error('Expected at least seven building profiles plus Datetime in each CSV file.');
end

if ~isequal(activePower.Datetime, powerFactor.Datetime)
    error('Active power and power factor timestamps do not match.');
end
end

function kvar = kwPfToKvar(kw, pf)
% Convert active power and power factor into reactive power magnitude.
if pf <= 0 || pf > 1
    error('Power factor must be in the interval (0, 1]. Received %.6f.', pf);
end

kvar = kw * tan(acos(pf));
end

function [busP, busQ] = collectBusPcElementPowers(DSSCircuit, allBusNames)
% Sum solved element powers onto the bus where each load or PV element is connected.
busP = zeros(1, numel(allBusNames));
busQ = zeros(1, numel(allBusNames));
elementNames = string(DSSCircuit.AllElementNames);

for elementIdx = 1:numel(elementNames)
    elementName = elementNames(elementIdx);
    if ~startsWith(elementName, "Load.", 'IgnoreCase', true) && ...
            ~startsWith(elementName, "PVSystem.", 'IgnoreCase', true)
        continue;
    end

    DSSCircuit.SetActiveElement(char(elementName));
    activeElement = DSSCircuit.ActiveCktElement;
    busNames = string(activeElement.BusNames);
    if isempty(busNames)
        continue;
    end

    busName = normalizeBusName(busNames(1));

    powers = activeElement.Powers;
    busIdx = find(strcmpi(allBusNames, busName), 1);
    if isempty(busIdx)
        continue;
    end

    busP(busIdx) = busP(busIdx) + sum(powers(1:2:end));
    busQ(busIdx) = busQ(busIdx) + sum(powers(2:2:end));
end
end

function busName = normalizeBusName(rawBusName)
% Strip phase suffixes such as ".1.2.3" to match OpenDSS bus names.
parts = split(string(rawBusName), ".");
busName = parts(1);
end

function busPowerTable = buildBusPowerTable(timestamps, busNames, busPowerKW, busPowerKvar)
% Convert dense per-step/per-bus matrices into a flat table for CSV export.
stepCount = numel(timestamps);
busCount = numel(busNames);

busPowerTable = table( ...
    repelem(timestamps, busCount, 1), ...
    repmat(busNames(:), stepCount, 1), ...
    reshape(busPowerKW.', [], 1), ...
    reshape(busPowerKvar.', [], 1), ...
    'VariableNames', {'Datetime', 'Bus', 'P_kW', 'Q_kvar'});
end

function appliedLoadTable = buildAppliedLoadTable(timestamps, loadGroups, appliedLoadRows)
% Record which building profile was assigned to which bus at each time step.
rowCount = size(appliedLoadRows, 1);
groupIdx = appliedLoadRows(:, 2);
stepIdx = appliedLoadRows(:, 1);
buildingProfile = strings(rowCount, 1);
bus = strings(rowCount, 1);

for rowIdx = 1:rowCount
    buildingProfile(rowIdx) = loadGroups(groupIdx(rowIdx)).building;
    bus(rowIdx) = loadGroups(groupIdx(rowIdx)).bus;
end

appliedLoadTable = table( ...
    timestamps(stepIdx), ...
    buildingProfile, ...
    bus, ...
    appliedLoadRows(:, 3), ...
    appliedLoadRows(:, 4), ...
    'VariableNames', {'Datetime', 'BuildingProfile', 'Bus', 'AssignedKW', 'AssignedKvar'});
assert(height(appliedLoadTable) == rowCount);
end

function cleanupOpenDSS(DSSObj)
% Release the COM server even if the script exits on an error.
try
    delete(DSSObj);
catch
end
end
