-- _filters/pub-summary.lua
-- Injects _summaries/<citekey>.md content into individual pub pages.
-- Bails early on any page not under bibliography/publications/.

local function get_input_file()
  if quarto and quarto.doc and quarto.doc.input_file then
    return quarto.doc.input_file
  end
  return ""
end

local function read_file(path)
  local f = io.open(path, "r")
  if not f then return nil end
  local content = f:read("*all")
  f:close()
  return content
end

-- Derive the project root from the absolute input file path.
-- The input file is something like /path/to/project/bibliography/publications/article/foo.qmd
-- We strip the "bibliography/publications/..." suffix to get the project root.
local function get_project_root(input_file)
  -- Match everything up to (but not including) "bibliography/"
  local root = string.match(input_file, "^(.*/)bibliography/publications/")
  return root
end

function Pandoc(doc)
  local input_file = get_input_file()

  if not string.match(input_file, "bibliography/publications/") then
    return doc
  end

  local citekey = string.match(input_file, "([^/\\]+)%.qmd$")
  if not citekey then return doc end

  local project_root = get_project_root(input_file)
  if not project_root then return doc end

  local summary_path = project_root .. "_summaries/" .. citekey .. ".md"
  local summary_text = read_file(summary_path)
  if not summary_text or summary_text == "" then return doc end

  local summary_doc = pandoc.read(summary_text, "markdown")

  local header = pandoc.Header(
    3,
    { pandoc.Str("Lab News Desk") },
    pandoc.Attr("", {}, {})
  )

  local disclosure = pandoc.Para({
    pandoc.Emph({
      pandoc.Str(
        "This summary was written by a large language model in a reporter-style, general-audience voice."
      )
    })
  })

  local inner = { header }
  for _, block in ipairs(summary_doc.blocks) do
    table.insert(inner, block)
  end
  table.insert(inner, disclosure)

  local styled_div = pandoc.Div(
    inner,
    pandoc.Attr("lab-news-desk", {}, {
      style = "background:#f8f9fa;border-left:4px solid #00205B;padding:1rem 1.5rem;margin-top:2rem;"
    })
  )

  local new_blocks = {}
  for _, block in ipairs(doc.blocks) do
    table.insert(new_blocks, block)
  end
  table.insert(new_blocks, styled_div)

  return pandoc.Pandoc(new_blocks, doc.meta)
end
