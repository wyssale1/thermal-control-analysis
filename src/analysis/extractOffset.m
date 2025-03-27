function [table, offset, t_stable, ambient_temp] = extractOffset(data, name)
%----------------------------------------------------------------
% Wrapper for extractOffsetWithAmbient function
% This redirects calls to the proper implementation
%----------------------------------------------------------------
    [table, offset, t_stable, ambient_temp] = extractOffsetWithAmbient(data, name);
end