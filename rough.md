 # try:
        #     #retrieve relevant memories
        #     memories = mem0.search(messages[-1].content,filters = {"user_id":user_id})

        #     #handle dict response format
        #     memory_list = memories['results']

        #     context = "relevant information from previous conversations:\n"
        #     for memory in memory_list:
        #         context += f"-{['memory']}\n"

        #     system_message = system_message(content=prompt_modifier(state))
        #     full_message = [system_message]+messages

        #     response = self.orchestrator_agent.invoke(full_message)

        #     try:
        #         interaction = [
        #             {
        #                 "role":"user",
        #                 "content":messages[-1].content
        #             },
        #             {
        #                 "role":"assistant",
        #                 "content": response.content
        #             }
        #         ]
        #         result = mem0.add(interaction,user_id = user_id)
        #         print(f"memory saved:{len(result.get('results',[]))} memories added")
        #     except Exception as e:
        #         print(f"Error saving memory:{e}")
        #     return {"messages":[response]}

        # except Exception as e:
        #     print(f"Error retrieving :{e}")

        #     #fallback response without memory context
        #     response = self.orchestrator_agent.invoke(state)



        # user_id = state.get("user_id", "default")
        # profile = self.get_user_profile(store, user_id)
        # #system_message
        # system_message = SystemMessage(
        #     content= prompt_modifier(state)
        # )
        # response = self.orchestrator_agent.invoke([system_message] + state["messages"])

        # if getattr(response, "tool_calls", None):
        #     return {"messages": [response], "next": "orchestrator_tools"}

        # if isinstance(state["messages"][-1], ToolMessage):
        #     return {"messages": [response], "next": END}

        # route = response.content.strip().lower()

        # if route not in ("gmail", "linkedin", "internet", "assistant"):
        #     route = "assistant"

        # return {"next": route}












        def orchestrator(self, state: State, store: BaseStore) -> dict[str, Any]:
        messages = state["messages"]
        user_id = state["user_id"]
        user_messages = messages[-1].content

        try:
            #retrieve relevant memories
            memories = memory.search(messages[-1].content,filters = {"user_id":user_id},top_k=5)

            #handle dict response format
            memory_list = memories.get("results",[])

            context = "relevant information from previous conversations:\n"
            for memory in memory_list:
                memory_context = "\n".join(
                    f"- {item['memory']}"
                    for item in memory_list
                    if item.get("memory")
                )

            system_message = SystemMessage(
                content =(
                    f"{prompt_modifier(state)}\n\n"
                    f"Relevant long term memories:\n{memory_context}"
                )
            )
            full_message = [system_message]+messages

            response = self.orchestrator_agent.invoke([system_message,"messages"])

            try:
                interaction = [
                    {"role":"user","content":messages[-1].content},
                    {"role":"assistant","content": response.content}
                ]
                result = memory.add(interaction,user_id = user_id)   #adding relevant interactions into the memory


                print(f"memory saved:{len(result.get('results',[]))} memories added")
            except Exception as e:
                print(f"Error saving memory:{e}")
            return {"messages":[response]}

        except Exception as e:
            print(f"Error retrieving :{e}")
            system_message = SystemMessage(content=prompt_modifier(state))

            #fallback response without memory context
            response = self.orchestrator_agent.invoke([system_message,*messages])
            return {"messages":[response]}