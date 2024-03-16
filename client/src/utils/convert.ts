import { ToolSection } from "@/stores/toolStore";

export const transformToolPanelView = (panelView: { [id: string]: ToolSection }) => {
    const keysArr = Object.keys(panelView);
    const newToolPanelViewMap: { [id: string]: ToolSection } = {};
    keysArr.map((i, index) => {
        const currentPv = panelView[i] as ToolSection;
        const { model_class, id, _parent_id } = currentPv;
        let nextIndex = index + 1;
        const nextPv = panelView[keysArr[nextIndex] as string];

        if (id && nextPv) {
            if (model_class === "ToolSectionLabel") {
                if (nextPv.model_class !== "ToolSectionLabel") {
                    let nextObj: ToolSection | undefined = nextPv;
                    while (nextObj && nextObj.model_class !== "ToolSectionLabel") {
                        nextObj._parent_id = id;
                        nextIndex++;
                        nextObj = panelView[keysArr[nextIndex] as string];
                    }
                }
                currentPv.tools = [];
                newToolPanelViewMap[id] = currentPv;
            } else {
                if (_parent_id) {
                    newToolPanelViewMap[_parent_id]?.tools?.push(currentPv);
                } else {
                    newToolPanelViewMap[id] = currentPv;
                }
            }
        }
    });
    return newToolPanelViewMap;
};
