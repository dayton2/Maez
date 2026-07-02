function [DSSCircuit, DSSSolution] = compileDSS(DSSObj, DSSText, masterFile)
    % compileDSS Clears OpenDSS and compiles the project Master.dss file.

    if ~isfile(masterFile)
        error('Master.dss not found: %s', masterFile);
    end

    DSSText.Command = 'clear';
    DSSText.Command = sprinf('compile "%s"', masterFile);

    if ~isempty(strtrim(DSSText.Result))
        fprintf('OpenDSS compile result: %s\n', DSSText.Result);
    end

    DSSCircuit = DSSObj.ActiveCircuit;
    DSSSolution = DSSCircuit.Solution;
end