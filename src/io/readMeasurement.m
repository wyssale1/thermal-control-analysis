function data = readMeas(filename, filepath)
%----------------------------------------------------------------
% Reads the data from the excel file
% Inputs: filename and filepath
% Outputs: data from the file in a matrix
% the columns of the excel files are:
% Time, Holder Temperature, Liquid Temperature, Target Temperature (Holder), Sink
% temperature, Room temperature, Power
%----------------------------------------------------------------
    try
        % First attempt: Try to read using readmatrix (newer MATLAB versions)
        data = readmatrix(filepath);
        fprintf('Successfully read data using readmatrix.\n');
    catch ME1
        try
            % Second attempt: Try to read using xlsread (older MATLAB versions)
            [num, ~, ~] = xlsread(filepath);
            data = num;
            fprintf('Successfully read data using xlsread.\n');
        catch ME2
            try
                % Third attempt: Try to use readtable and convert
                T = readtable(filepath);
                data = table2array(T);
                fprintf('Successfully read data using readtable.\n');
            catch ME3
                % Fourth attempt: Manual parsing as last resort
                try
                    fprintf('Standard import methods failed. Trying manual file reading...\n');
                    fid = fopen(filepath, 'r');
                    if fid == -1
                        error('Could not open file');
                    end
                    
                    % Read the entire file as text
                    file_content = fscanf(fid, '%c');
                    fclose(fid);
                    
                    % Split the content into lines
                    lines = splitlines(file_content);
                    
                    % Find the first line with numbers
                    data_start_line = 1;
                    while data_start_line <= length(lines)
                        line = lines{data_start_line};
                        % Check if line has numbers
                        if ~isempty(regexp(line, '\d+\.\d+', 'once'))
                            break;
                        end
                        data_start_line = data_start_line + 1;
                    end
                    
                    if data_start_line > length(lines)
                        error('No data found in file');
                    end
                    
                    % Parse all data lines
                    data = [];
                    for i = data_start_line:length(lines)
                        line = lines{i};
                        if isempty(line) || ~any(isstrprop(line, 'digit'))
                            continue; % Skip empty or non-numeric lines
                        end
                        
                        % Parse numbers from the line
                        tokens = regexp(line, '-?\d+\.?\d*', 'match');
                        if length(tokens) >= 7
                            row = str2double(tokens(1:7));
                            data = [data; row];
                        end
                    end
                    fprintf('Successfully read data using manual parsing.\n');
                catch ME4
                    % If all methods fail, provide detailed error
                    error('All import methods failed. Error details:\n%s\n%s\n%s\n%s', ...
                          ME1.message, ME2.message, ME3.message, ME4.message);
                end
            end
        end
    end
    
    % Ensure we have data
    if isempty(data)
        error('No data was read from the file.');
    end
    
    % Ensure we have all 7 columns
    if size(data, 2) < 7
        warning('Data has fewer than 7 columns (%d columns found).', size(data, 2));
        % Pad with NaN if needed
        if size(data, 2) < 7
            data = [data, NaN(size(data, 1), 7 - size(data, 2))];
            warning('Padded missing columns with NaN.');
        end
    elseif size(data, 2) > 7
        warning('Data has more than 7 columns (%d columns found). Using first 7 columns.', size(data, 2));
        data = data(:, 1:7);
    end
    
    % Remove any rows with NaN values
    nan_rows = any(isnan(data), 2);
    if any(nan_rows)
        warning('Removing %d rows with NaN values.', sum(nan_rows));
        data = data(~nan_rows, :);
    end
    
    % Ensure we still have data after cleaning
    if isempty(data)
        error('No valid data remains after removing rows with NaN values.');
    end
    
    fprintf('Final data matrix has %d rows and %d columns.\n', size(data, 1), size(data, 2));
end

function lines = splitlines(str)
% Splits string by newline character
    if isempty(str)
        lines = {''};
        return;
    end

    % Handle different newline formats
    str = strrep(str, sprintf('\r\n'), sprintf('\n'));
    str = strrep(str, sprintf('\r'), sprintf('\n'));
    
    % Split by newline
    lines = strsplit(str, sprintf('\n'));
    
    % Remove empty lines at the end
    while ~isempty(lines) && isempty(lines{end})
        lines(end) = [];
    end
end