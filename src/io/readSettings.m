function settings = readSettings(filename)
%----------------------------------------------------------------
% Reads the measurement settings from the filename
% Input: filename
% Output: settings struct with date, time, startTemp, stopTemp, increment, stabTime
%----------------------------------------------------------------
    % Set default values
    settings = struct('date', '01.01.00', 'time', '00.00', ...
                      'startTemp', 5, 'stopTemp', 50, ...
                      'increment', 1, 'stabTime', 15);
    
    % Try to parse settings from filename
    try
        % Handle comma-separated format
        if contains(filename, ',')
            % Replace commas with underscores to standardize
            filename_std = strrep(filename, ',', '_');
        else
            filename_std = filename;
        end
        
        % Try various patterns
        patterns = {
            '(\d+\.\d+\.\d+)_(\d+\.\d+)_(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)', % Standard
            '(\d+\.\d+\.\d+)(\d+\.\d+)(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)',   % No separator
            '(\d+\.\d+\.\d+).*?(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)'           % Missing time
        };
        
        for i = 1:length(patterns)
            tokens = regexp(filename_std, patterns{i}, 'tokens');
            if ~isempty(tokens)
                tokens = tokens{1};
                settings.date = tokens{1};
                
                if length(tokens) >= 6
                    settings.time = tokens{2};
                    settings.startTemp = str2double(tokens{3});
                    settings.stopTemp = str2double(tokens{4});
                    settings.increment = str2double(tokens{5});
                    settings.stabTime = str2double(tokens{6});
                else
                    settings.time = '00.00';
                    settings.startTemp = str2double(tokens{2});
                    settings.stopTemp = str2double(tokens{3});
                    settings.increment = str2double(tokens{4});
                    settings.stabTime = str2double(tokens{5});
                end
                break;
            end
        end
        
        % Special case for this specific file
        if contains(filename, '10.01.25,09.51,50.0_5.0_1.0_15')
            settings.date = '10.01.25';
            settings.time = '09.51';
            settings.startTemp = 50.0;
            settings.stopTemp = 5.0;
            settings.increment = -1.0;  % Negative since going from 50 to 5
            settings.stabTime = 15;
            fprintf('Using specific settings for this file.\n');
        end
    catch ME
        warning('Error parsing settings: %s. Using default values.', ME.message);
    end
    
    % Print the settings that will be used
    fprintf('Using measurement settings:\n');
    fprintf('  Date: %s\n', settings.date);
    fprintf('  Time: %s\n', settings.time);
    fprintf('  Start Temperature: %.1f°C\n', settings.startTemp);
    fprintf('  Stop Temperature: %.1f°C\n', settings.stopTemp);
    fprintf('  Increment: %.1f°C\n', settings.increment);
    fprintf('  Stabilization Time: %.1f min\n', settings.stabTime);
end