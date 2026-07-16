document.addEventListener('DOMContentLoaded',()=>{
  const button=document.getElementById('translateProjectObjects');
  if(button)button.onclick=()=>translateAllProjectObjects();
  if(typeof renderGraph==='function'){
    const originalRenderGraph=renderGraph;
    renderGraph=function(){
      originalRenderGraph();
      document.querySelectorAll('#graphNodes .graph-node').forEach(element=>{
        const node=state.graph?.nodes.find(item=>item.object_id===element.dataset.id);
        const translated=state.objectTranslationsById?.[element.dataset.id];
        const label=translated?.translated_text||node?.title;
        const text=element.querySelectorAll('text');
        if(label&&text.length>1)text[text.length-1].textContent=label.length>24?label.slice(0,22)+'…':label;
      });
    };
  }
});
