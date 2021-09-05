local function new_with_colors(name, color1, color2) 
    path = "frame.svg"
    local file = io.open(path)
    local content = file:read("*all")
    file:close()

    local function replace_color(s, index, new)
        pattern = "<stop  offset=\""..index.."\" style=\"stop.color:#(......)\"/>"
        replacement = "<stop  offset=\""..index.."\" style=\"stop-color:#"..new.."\"/>"
        replaced, n = s:gsub(pattern, replacement)
        return replaced
    end

    local new_content = ""
    for line in io.lines(path) do
        new_line = replace_color(line, 0, color1)
        new_line = replace_color(new_line, 1, color2)
        new_content = new_content .. new_line .. "\n"
    end

    local new_file = io.open("frames/frame-"..name..".svg",'w')
    new_file:write(new_content)
    new_file:close()
end

local function build()
    new_with_colors("berserker", "000000", "C8000F")

    -- tex.print("test")
end

return {build = build}
