-- Meow for E-Kittens
-- Hotkey sends a browser-source event. overlay.html plays the burst.

local obs = obslua

local ctx = {
  hotkey = obs.OBS_INVALID_HOTKEY_ID,
  source_name = "",
}

local function source_kind(source)
  local ok, kind = pcall(function()
    return obs.obs_source_get_unversioned_id(source)
  end)
  if ok and kind ~= nil and kind ~= "" then
    return kind
  end
  return obs.obs_source_get_id(source)
end

local function add_browser_sources(list)
  local sources = obs.obs_enum_sources()
  if sources == nil then
    return 0
  end

  local count = 0
  for _, source in ipairs(sources) do
    if source_kind(source) == "browser_source" then
      local name = obs.obs_source_get_name(source)
      obs.obs_property_list_add_string(list, name, name)
      count = count + 1
    end
  end

  obs.source_list_release(sources)
  return count
end

local function trigger()
  if ctx.source_name == nil or ctx.source_name == "" then
    obs.script_log(obs.LOG_WARNING, "Choose the kitten browser source in Tools -> Scripts.")
    return
  end

  local source = obs.obs_get_source_by_name(ctx.source_name)
  if source == nil then
    obs.script_log(obs.LOG_WARNING, "Browser source not found: " .. ctx.source_name)
    return
  end

  if source_kind(source) ~= "browser_source" then
    obs.obs_source_release(source)
    obs.script_log(obs.LOG_WARNING, "Selected source is not a browser source.")
    return
  end

  local handler = obs.obs_source_get_proc_handler(source)
  local cd = obs.calldata_create()
  obs.calldata_set_string(cd, "eventName", "meowBurst")
  obs.calldata_set_string(cd, "jsonString", "{}")
  local called = obs.proc_handler_call(handler, "javascript_event", cd)
  obs.calldata_destroy(cd)
  obs.obs_source_release(source)

  if called then
    obs.script_log(obs.LOG_INFO, "Playing kitten burst on " .. ctx.source_name)
  else
    obs.script_log(obs.LOG_WARNING, "Could not reach the browser source. Leave it visible and turn off shutdown-when-not-visible.")
  end
end

local function on_hotkey(pressed)
  if pressed then
    trigger()
  end
end

local function on_play_clicked()
  trigger()
  return false
end

local function on_reload_sources()
  return true
end

function script_description()
  return [[Plays a 3 second burst of 3-6 kittens on a Browser Source.

1. Add a Browser Source for overlay.html, sized to the canvas, above the game, eye icon on.
2. Leave "Shutdown source when not visible" and "Refresh browser when scene becomes active" unchecked.
3. Select that source below.
4. Bind "Meow for E-Kittens" under Settings -> Hotkeys.

The burst is only in the OBS preview and on stream. Pressing the hotkey again restarts it.]]
end

function script_properties()
  local props = obs.obs_properties_create()
  local list = obs.obs_properties_add_list(
    props,
    "source",
    "Browser source",
    obs.OBS_COMBO_TYPE_LIST,
    obs.OBS_COMBO_FORMAT_STRING
  )

  if add_browser_sources(list) == 0 then
    obs.obs_property_list_add_string(list, "(no browser source yet)", "")
  end

  obs.obs_properties_add_button(props, "reload_sources", "Reload source list", on_reload_sources)
  obs.obs_properties_add_button(props, "play", "Play kitten burst", on_play_clicked)
  return props
end

function script_defaults(settings)
  obs.obs_data_set_default_string(settings, "source", "")
end

function script_update(settings)
  ctx.source_name = obs.obs_data_get_string(settings, "source")
end

function script_load(settings)
  ctx.hotkey = obs.obs_hotkey_register_frontend(
    "meow_for_e_kittens.trigger",
    "Meow for E-Kittens",
    on_hotkey
  )
  local saved = obs.obs_data_get_array(settings, "meow_for_e_kittens.trigger")
  obs.obs_hotkey_load(ctx.hotkey, saved)
  obs.obs_data_array_release(saved)
  ctx.source_name = obs.obs_data_get_string(settings, "source")
end

function script_save(settings)
  local saved = obs.obs_hotkey_save(ctx.hotkey)
  obs.obs_data_set_array(settings, "meow_for_e_kittens.trigger", saved)
  obs.obs_data_array_release(saved)
end

function script_unload()
  if ctx.hotkey ~= obs.OBS_INVALID_HOTKEY_ID then
    obs.obs_hotkey_unregister(on_hotkey)
    ctx.hotkey = obs.OBS_INVALID_HOTKEY_ID
  end
end
