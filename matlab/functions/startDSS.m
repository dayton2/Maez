function [DSSObj, DSSText] = startDSS()
    % startDSS starts the official EPRI OpenDSS COM server from MATLAB.
    %
    % Requires:
    % - Windows
    % - OpenDSS installed and COM server registered
    % - 64-bit OpenDSS if using 64-bit MATLAB

    DSSObj = actxserver('OpenDSSEngine.DSS');
    if ~DSSObj.Start(0)
        error('OpenDSS failed to start. Check OpenDSS installation and COM registration.');
    end

    DSSText = DSSObj.Text;
end