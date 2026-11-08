-- name: The Misanthropic Cow
-- description: Play as The Misanthropic Cow, with her own idle, walk, run, sneak, jump, fall, landing, skid, hurt, death and victory animations.\n\nType /cow to switch her on or off.

-- Her model (built from actors/misanthropic_cow/)
local E_MODEL_COW = smlua_model_util_get_id("misanthropic_cow_geo")

-- Her hip height in model units. The game scales its animations' body movement by this,
-- so Mario's animations fit her longer legs and her own animations play at their real size.
local COW_HIP_HEIGHT = 455
local DEFAULT_HIP_HEIGHT = 189

-- Which of the game's animations she replaces with her own
local REPLACE = {
    [MARIO_ANIM_IDLE_HEAD_LEFT]         = "cow_idle",
    [MARIO_ANIM_IDLE_HEAD_RIGHT]        = "cow_idle",
    [MARIO_ANIM_IDLE_HEAD_CENTER]       = "cow_idle",
    [MARIO_ANIM_WALKING]                = "cow_walk",
    [MARIO_ANIM_RUNNING]                = "cow_run",
    [MARIO_ANIM_TIPTOE]                 = "cow_sneak",
    [MARIO_ANIM_START_TIPTOE]           = "cow_sneak",
    [MARIO_ANIM_SINGLE_JUMP]            = "cow_jump",
    [MARIO_ANIM_GENERAL_FALL]           = "cow_fall",
    [MARIO_ANIM_LAND_FROM_SINGLE_JUMP]  = "cow_land",
    [MARIO_ANIM_GENERAL_LAND]           = "cow_land",
    [MARIO_ANIM_SKID_ON_GROUND]         = "cow_skid",
    [MARIO_ANIM_SOFT_BACK_KB]           = "cow_hurt",
    [MARIO_ANIM_SOFT_FRONT_KB]          = "cow_hurt",
    [MARIO_ANIM_DYING_ON_BACK]          = "cow_death",
    [MARIO_ANIM_DYING_ON_STOMACH]       = "cow_death",
    [MARIO_ANIM_DYING_FALL_OVER]        = "cow_death",
    [MARIO_ANIM_STAR_DANCE]             = "cow_victory",
}

for i = 0, MAX_PLAYERS - 1 do
    gPlayerSyncTable[i].cowOn = true
end

local function mario_update(m)
    local o = m.marioObj
    if gPlayerSyncTable[m.playerIndex].cowOn then
        obj_set_model_extended(o, E_MODEL_COW)
        m.unkB0 = COW_HIP_HEIGHT
        o.header.gfx.animInfo.animYTrans = COW_HIP_HEIGHT
        local name = REPLACE[o.header.gfx.animInfo.animID]
        if name ~= nil then
            smlua_anim_util_set_animation(o, name)
        end
    elseif m.unkB0 == COW_HIP_HEIGHT then
        m.unkB0 = DEFAULT_HIP_HEIGHT
        o.header.gfx.animInfo.animYTrans = DEFAULT_HIP_HEIGHT
    end
end

local function on_cow_command(msg)
    local s = gPlayerSyncTable[0]
    if msg == "on" then s.cowOn = true
    elseif msg == "off" then s.cowOn = false
    else s.cowOn = not s.cowOn end
    djui_chat_message_create(s.cowOn and "The Misanthropic Cow: on" or "The Misanthropic Cow: off")
    return true
end

hook_event(HOOK_MARIO_UPDATE, mario_update)
hook_chat_command("cow", "[on|off] - play as The Misanthropic Cow", on_cow_command)
